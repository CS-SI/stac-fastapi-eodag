# -*- coding: utf-8 -*-
# Copyright 2023, CS GROUP - France, https://www.cs-soprasteria.com
#
# This file is part of stac-fastapi-eodag project
#     https://www.github.com/CS-SI/stac-fastapi-eodag
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
"""Item crud client."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any, Optional, cast
from urllib.parse import unquote_plus

import attr
import cql2
import orjson
from fastapi import HTTPException
from pydantic import ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError
from pygeofilter.parsers.cql2_json import parse as parse_json
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.search import BaseSearchPostRequest
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes

from eodag import EOProduct, SearchResult
from eodag.api.collection import Collection as EodagCollection
from eodag.api.collection import CollectionsList
from eodag.plugins.search.build_search_result import ECMWFSearch
from stac_fastapi.eodag.client import CustomCoreClient
from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.constants import DEFAULT_LIMIT
from stac_fastapi.eodag.cql_evaluate import EodagEvaluator
from stac_fastapi.eodag.errors import NoMatchingCollection, ResponseSearchError
from stac_fastapi.eodag.models.item import create_stac_item
from stac_fastapi.eodag.models.links import (
    CollectionLinks,
    CollectionSearchPagingLinks,
    ItemCollectionLinks,
    PagingLinks,
)
from stac_fastapi.eodag.models.stac_metadata import CommonStacMetadata
from stac_fastapi.eodag.utils import (
    format_datetime_range,
    is_dict_str_any,
    str2json,
)

if TYPE_CHECKING:
    from typing import Union

    from fastapi import Request
    from pydantic import BaseModel

    from eodag.api.product._product import EOProduct

    NumType = Union[float, int]


logger = logging.getLogger(__name__)


@attr.s
class EodagCoreClient(CustomCoreClient):
    """"""

    post_request_model: type[BaseModel] = attr.ib(default=BaseSearchPostRequest)
    stac_metadata_model: type[CommonStacMetadata] = attr.ib(default=CommonStacMetadata)

    def _format_collection(self, collection: EodagCollection, request: Request) -> Collection:
        """Convert a EODAG STAC collection to a STAC collection for API."""

        # keep only federation backends which allow order mechanism
        # to create "retrieve" collection links from them
        # TODO: this needs to be changed: we cannot request the search plugins for each collection, it is too costly.
        # TODO: We should find a way to know which federation backends support
        # the order mechanism without requesting the plugins manager
        def has_ecmwf_search_plugin(federation_backends, request):
            for fb in federation_backends:
                search_plugins = request.app.state.dag._plugins_manager.get_search_plugins(provider=fb)
                if any(isinstance(plugin, ECMWFSearch) for plugin in search_plugins):
                    return True
            return False

        extension_names = [type(ext).__name__ for ext in self.extensions]

        federation_backends = set(
            request.app.state.dag.db.get_federation_backends(collection=collection._id, enabled=True)
        )
        if self.extension_is_enabled("CollectionOrderExtension") and not has_ecmwf_search_plugin(
            federation_backends, request
        ):
            extension_names.remove("CollectionOrderExtension")

        coll_dict = collection.model_dump(mode="json", exclude={"alias", "eodag_stac_collection"})
        for link in coll_dict["links"]:
            if link.get("label:assets") is None:
                link.pop("label:assets")
        assets = coll_dict.get("assets")
        if isinstance(assets, dict):
            for asset in assets.values():
                if asset.get("description") is None:
                    asset.pop("description", None)

        # add API-required links
        all_coll_links = CollectionLinks(
            collection_id=collection.id,
            request=request,
        ).get_links(extensions=extension_names, extra_links=coll_dict["links"])

        # remove eodag-specific fields
        coll_dict["links"] = all_coll_links
        return Collection(**coll_dict)

    async def _search_base(self, search_request: BaseSearchPostRequest, request: Request) -> ItemCollection:
        eodag_args = prepare_search_base_args(search_request=search_request, model=self.stac_metadata_model)

        request.state.eodag_args = eodag_args

        # validate request
        settings = get_settings()
        validate: bool = settings.validate_request

        # check if the collection exists
        if collection := eodag_args.get("collection"):
            all_coll = await asyncio.to_thread(request.app.state.dag.list_collections)
            # only check the first collection (EODAG search only support a single collection)
            existing_coll = [coll for coll in all_coll if coll.id == collection]
            if not existing_coll:
                raise NoMatchingCollection(f"Collection {collection} does not exist.")
            eodag_args["collection"] = existing_coll[0].id
        else:
            raise HTTPException(status_code=400, detail="A collection is required")

        if ids := eodag_args.pop("ids", []):
            # get products by ids
            search_result = SearchResult([])
            for item_id in ids:
                eodag_args["id"] = item_id
                result = await asyncio.to_thread(request.app.state.dag.search, validate=validate, **eodag_args)
                search_result.extend(result)
            search_result.number_matched = len(search_result)
        elif eodag_args.get("token") and eodag_args.get("provider"):
            # search with pagination
            search_result = await asyncio.to_thread(eodag_search_next_page, request.app.state.dag, eodag_args)
        else:
            # search without ids or pagination
            search_result = await asyncio.to_thread(request.app.state.dag.search, validate=validate, **eodag_args)

        if search_result.errors and not len(search_result):
            raise ResponseSearchError(search_result.errors, self.stac_metadata_model)

        request_json = await request.json() if request.method == "POST" else None

        features: list[Item] = []
        extension_names = [type(ext).__name__ for ext in self.extensions]

        for product in search_result:
            feature = create_stac_item(
                product, self.stac_metadata_model, self.extension_is_enabled, request, extension_names, request_json
            )
            features.append(feature)

        feature_collection = ItemCollection(
            type="FeatureCollection",
            features=features,
            numberMatched=search_result.number_matched,
            numberReturned=len(features),
        )

        # pagination
        if "provider" not in request.state.eodag_args and len(search_result) > 0:
            request.state.eodag_args["provider"] = search_result[-1].provider
        feature_collection["links"] = PagingLinks(
            request=request,
            next=search_result.next_page_token,
            federation_backend=request.state.eodag_args.get("provider"),
        ).get_links(request_json=request_json, extensions=extension_names)
        return feature_collection

    async def all_collections(
        self,
        request: Request,
        bbox: Optional[list[NumType]] = None,
        datetime: Optional[str] = None,
        limit: Optional[int] = 10,
        # Extensions
        offset: Optional[int] = 0,
        q: Optional[list[str]] = None,
        sortby: Optional[list[str]] = None,
        filter_expr: Optional[str] = None,
        filter_lang: Optional[str] = None,
        **kwargs: Any,
    ) -> Collections:
        """
        Get all collections from EODAG.

        :param request: The request object.
        :param bbox: Bounding box to filter the collections.
        :param datetime: Date and time range to filter the collections.
        :param limit: Maximum number of collections to return.
        :param offset: Starting position from which to return collections.
        :param q: Query string to filter the collections.
        :param query: Query string to filter the search.
        :param sortby: List of fields to sort the results by.
        :param filter_expr: CQL filter to apply to the search.
        :param filter_lang: Language of the filter.
        :returns: All collections.
        :raises HTTPException: If the unsupported bbox parameter is provided.
        """
        base_url = get_base_url(request)

        next_link: Optional[dict[str, Any]] = None
        prev_link: Optional[dict[str, Any]] = None
        first_link: Optional[dict[str, Any]] = None

        cql2_json = None
        if filter_expr:
            if filter_lang == "cql2-text":
                cql2_json = cql2.parse_text(filter_expr).to_json()
            elif filter_lang == "cql2-json":
                cql2_json = str2json("filter_expr", filter_expr)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported filter_lang {filter_lang}")

        if not self.extension_is_enabled("OffsetPaginationExtension"):
            limit = None

        collections = cast(
            CollectionsList,
            await asyncio.to_thread(
                request.app.state.dag.list_collections,
                geometry=bbox,
                datetime=datetime,
                limit=limit,
                q=" ".join(q) if q else None,
                cql2_json=cql2_json,
                sortby=sortby,
            ),
        )

        number_matched = cast(int, collections.number_matched)

        links = [
            {
                "rel": Relations.root,
                "type": MimeTypes.json,
                "href": base_url,
                "title": get_settings().stac_fastapi_title,
            },
        ]

        if self.extension_is_enabled("OffsetPaginationExtension"):
            limit = limit if limit is not None else 10
            offset = offset if offset is not None else 0

            collections = collections[offset : offset + limit]
            # info about number matched was lost during the slice, then restore it
            # TODO: find a way to not lose it during the slice
            collections.number_matched = number_matched

            if offset + limit < collections.number_matched:
                next_link = {"body": {"limit": limit, "offset": offset + limit}}

            if offset > 0:
                prev_link = {"body": {"limit": limit, "offset": max(0, offset - limit)}}

            first_link = {"body": {"limit": limit, "offset": 0}}

        # format collections
        formatted_collections = [self._format_collection(coll, request) for coll in collections]

        extension_names = [type(ext).__name__ for ext in self.extensions]

        paging_links = CollectionSearchPagingLinks(
            request=request, next=next_link, prev=prev_link, first=first_link
        ).get_links(extensions=extension_names)

        links.extend(paging_links)

        return Collections(
            collections=formatted_collections,
            links=links,
            numberMatched=collections.number_matched,
            numberReturned=len(collections),
        )

    async def get_collection(self, collection_id: str, request: Request, **kwargs: Any) -> Collection:
        """
        Get collection by id.

        Called with ``GET /collections/{collection_id}``.

        :param collection_id: ID of the collection.
        :param request: The request object.
        :param kwargs: Additional arguments.
        :returns: The collection.
        :raises NotFoundError: If the collection does not exist.
        """
        collection = cast(
            Optional[EodagCollection], await asyncio.to_thread(request.app.state.dag.get_collection, id=collection_id)
        )

        if collection is None:
            raise NotFoundError(f"Collection {collection_id} does not exist.")

        return self._format_collection(collection, request)

    async def item_collection(
        self,
        collection_id: str,
        request: Request,
        bbox: Optional[list[NumType]] = None,
        datetime: Optional[str] = None,
        limit: Optional[int] = None,
        # extensions
        sortby: Optional[list[str]] = None,
        filter_expr: Optional[str] = None,
        filter_lang: Optional[str] = "cql2-text",
        token: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> ItemCollection:
        """
        Get all items from a specific collection.

        Called with ``GET /collections/{collection_id}/items``.

        :param collection_id: ID of the collection.
        :param request: The request object.
        :param bbox: Bounding box to filter the items.
        :param datetime: Date and time range to filter the items.
        :param limit: Maximum number of items to return.
        :param sortby: List of fields to sort the results by.
        :param filter_expr: CQL filter to apply to the search.
        :param filter_lang: Language of the filter (default is "cql2-text").
        :param token: Page token for pagination.
        :param kwargs: Additional arguments.
        :returns: An ItemCollection.
        :raises NotFoundError: If the collection does not exist.
        """

        base_args = {"collections": [collection_id], "bbox": bbox, "datetime": datetime, "limit": limit, "token": token}

        clean = self._clean_search_args(
            base_args, sortby=sortby, filter_expr=filter_expr, filter_lang=filter_lang, query=query
        )

        search_request = self.post_request_model.model_validate(clean)
        item_collection = cast(ItemCollection, await self._search_base(search_request, request))
        extension_names = [type(ext).__name__ for ext in self.extensions]
        extra_links = item_collection.get("links", [])
        links = ItemCollectionLinks(collection_id=collection_id, request=request).get_links(
            extensions=extension_names, extra_links=extra_links
        )
        item_collection["links"] = links
        return item_collection

    async def post_search(
        self, search_request: BaseSearchPostRequest, request: Request, **kwargs: Any
    ) -> ItemCollection:
        """
        Handle POST search requests.

        :param search_request: The search request parameters.
        :param request: The HTTP request object.
        :param kwargs: Additional keyword arguments.
        :returns: Found items.
        """
        return await self._search_base(search_request, request)

    async def get_search(
        self,
        request: Request,
        collections: Optional[list[str]] = None,
        ids: Optional[list[str]] = None,
        bbox: Optional[list[NumType]] = None,
        intersects: Optional[str] = None,
        datetime: Optional[str] = None,
        limit: Optional[int] = None,
        # Extensions
        query: Optional[str] = None,
        sortby: Optional[list[str]] = None,
        filter_expr: Optional[str] = None,
        filter_lang: Optional[str] = "cql2-text",
        token: Optional[str] = None,
        **kwargs: Any,
    ) -> ItemCollection:
        """
        Handles the GET search request for STAC items.

        :param request: The request object.
        :param collections: List of collection IDs to include in the search.
        :param ids: List of item IDs to include in the search.
        :param bbox: Bounding box to filter the search.
        :param intersects: GeoJSON geometry to filter the search.
        :param datetime: Date and time range to filter the search.
        :param limit: Maximum number of items to return.
        :param query: Query string to filter the search.
        :param sortby: List of fields to sort the results by.
        :param filter_expr: CQL filter to apply to the search.
        :param filter_lang: Language of the filter.
        :param token: Page token for pagination.
        :param kwargs: Additional arguments.
        :returns: Found items.
        :raises HTTPException: If the provided parameters are invalid.
        """
        base_args = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "token": token,
        }

        clean = self._clean_search_args(
            base_args,
            intersects=intersects,
            datetime=datetime,
            sortby=sortby,
            query=query,
            filter_expr=filter_expr,
            filter_lang=filter_lang,
        )

        try:
            search_request = self.post_request_model(**clean)
        except ValidationError as err:
            raise HTTPException(status_code=400, detail=f"Invalid parameters provided {err}") from err

        return await self._search_base(search_request, request)

    async def get_item(self, item_id: str, collection_id: str, request: Request, **kwargs: Any) -> Item:
        """
        Get item by ID.

        :param item_id: ID of the item.
        :param collection_id: ID of the collection.
        :param request: The request object.
        :param kwargs: Additional arguments.
        :returns: The item.
        :raises NotFoundError: If the item does not exist.
        """

        search_request = self.post_request_model(ids=[item_id], collections=[collection_id], limit=1)
        item_collection = await self._search_base(search_request, request)
        if not item_collection["features"]:
            raise NotFoundError(f"Item {item_id} in Collection {collection_id} does not exist.")

        return Item(**item_collection["features"][0])

    def _clean_search_args(
        self,
        base_args: dict[str, Any],
        intersects: Optional[str] = None,
        datetime: Optional[str] = None,
        sortby: Optional[list[str]] = None,
        query: Optional[str] = None,
        filter_expr: Optional[str] = None,
        filter_lang: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Clean up search arguments to match format expected by pgstac"""
        if filter_expr:
            if filter_lang == "cql2-text":
                base_args["filter"] = cql2.parse_text(filter_expr).to_json()
            elif filter_lang == "cql2-json":
                base_args["filter"] = str2json("filter_expr", filter_expr)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported filter_lang {filter_lang}")
            base_args["filter_lang"] = "cql2-json"

        if datetime:
            base_args["datetime"] = format_datetime_range(datetime)

        if query:
            base_args["query"] = orjson.loads(unquote_plus(query))

        if intersects:
            base_args["intersects"] = orjson.loads(unquote_plus(intersects))

        if sortby:
            sort_param = []
            for sort in sortby:
                sortparts = re.match(r"^([+-]?)(.*)$", sort)
                if sortparts:
                    sort_param.append(
                        {
                            "field": sortparts.group(2).strip(),
                            "direction": "desc" if sortparts.group(1) == "-" else "asc",
                        }
                    )
            base_args["sortby"] = sort_param

        # Remove None values from dict
        clean = {}
        for k, v in base_args.items():
            if v is not None and v != []:
                clean[k] = v

        return clean


def prepare_search_base_args(search_request: BaseSearchPostRequest, model: type[CommonStacMetadata]) -> dict[str, Any]:
    """Prepare arguments for an eodag search based on a search request

    :param search_request: the search request
    :param model: the model used to validate stac metadata
    :returns: a dictionary containing arguments for the eodag search
    """
    if search_request.ids is None:
        base_args = search_request.model_dump()
        base_args["raise_errors"] = False
        base_args["count"] = get_settings().count
    else:
        base_args = {}

    # parse "sortby" search request attribute if it exists to make it work for an eodag search
    sort_by = {}
    if sortby := base_args.pop("sortby", None):
        param_tuples = []
        for param in sortby:
            param_tuples.append(
                (
                    model.to_eodag(param["field"]),
                    param["direction"],
                )
            )
        sort_by["sort_by"] = param_tuples

    eodag_query = {}
    if query_attr := base_args.pop("query", None):
        parsed_query = parse_query(query_attr)
        eodag_query = {model.to_eodag(k): v for k, v in parsed_query.items()}

    # get the extracted CQL2 properties dictionary if the CQL2 filter exists
    eodag_filter = {}
    base_args.pop("filter_lang", None)
    if f := base_args.pop("filter_expr", None):
        parsed_filter = parse_cql2(f)
        eodag_filter = {model.to_eodag(k): v for k, v in parsed_filter.items()}

    # EODAG search support a single collection
    if collections := base_args.pop("collections", search_request.collections):
        base_args["collection"] = collections[0]

    if search_request.ids:
        base_args["ids"] = search_request.ids

    # merge all eodag search arguments
    base_args = base_args | sort_by | eodag_filter | eodag_query
    base_args = {k: v for k, v in base_args.items() if v is not None}  # remove parameters with value None

    return base_args


def parse_query(query: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a STAC query parameter filter with the "eq", "lte" or "in" operator to a dict.

    :param query: The query parameter filter.
    :returns: The parsed query.
    """

    def add_error(error_message: str, input: Any) -> None:
        errors.append(
            InitErrorDetails(
                type=PydanticCustomError("invalid_query", error_message),  # type: ignore
                loc=("query",),
                input=input,
            )
        )

    query_props: dict[str, Any] = {}
    errors: list[InitErrorDetails] = []
    for property_name, conditions in cast(dict[str, Any], query).items():
        # Remove the prefix "properties." if present
        prop = property_name.replace("properties.", "", 1)

        # Check if exactly one operator is specified per property
        if not is_dict_str_any(conditions) or len(conditions) != 1:  # type: ignore
            add_error(
                "Exactly 1 operator must be specified per property",
                query[property_name],
            )
            continue

        # Retrieve the operator and its value
        operator, value = next(iter(cast(dict[str, Any], conditions).items()))

        # Validate the operator
        # only eq, in and lte are allowed
        # lte is only supported with eo:cloud_cover
        # eo:cloud_cover only accept lte operator
        if (
            operator not in ("eq", "lte", "in")
            or (operator == "lte" and prop != "eo:cloud_cover")
            or (prop == "eo:cloud_cover" and operator != "lte")
        ):
            add_error(
                f'operator "{operator}" is not supported for property "{prop}"',
                query[property_name],
            )
            continue
        if operator == "in" and not isinstance(value, list):
            add_error(
                f'operator "{operator}" requires a value of type list for property "{prop}"',
                query[property_name],
            )
            continue

        query_props[prop] = value

    if errors:
        raise ValidationError.from_exception_data(title="EODAGSearch", line_errors=errors)

    return query_props


def parse_cql2(filter_: dict[str, Any]) -> dict[str, Any]:
    """Process CQL2 filter

    :param filter_: The CQL2 filter.
    :returns: The parsed CQL2 filter
    """

    def add_error(error_message: str) -> None:
        errors.append(
            InitErrorDetails(
                type=PydanticCustomError("value_error", error_message),  # type: ignore
                loc=("filter",),
            )
        )

    errors: list[InitErrorDetails] = []
    try:
        parsing_result = EodagEvaluator().evaluate(parse_json(filter_))  # type: ignore
    except (ValueError, NotImplementedError) as e:
        add_error(str(e))
        raise ValidationError.from_exception_data(title="stac-fastapi-eodag", line_errors=errors) from e

    if not is_dict_str_any(parsing_result):
        add_error("The parsed filter is not a proper dictionary")
        raise ValidationError.from_exception_data(title="stac-fastapi-eodag", line_errors=errors)

    cql_args: dict[str, Any] = cast(dict[str, Any], parsing_result)

    invalid_keys = {
        "collections": 'Use "collection" instead of "collections"',
        "ids": 'Use "id" instead of "ids"',
    }
    for k, m in invalid_keys.items():
        if k in cql_args:
            add_error(m)

    if errors:
        raise ValidationError.from_exception_data(title="stac-fastapi-eodag", line_errors=errors)

    return cql_args


def eodag_search_next_page(dag, eodag_args):
    """Perform an eodag search with pagination.

    :param dag: The EODAG instance.
    :param eodag_args: The EODAG search arguments.
    :returns: The search result for the next page.
    """
    eodag_args = eodag_args.copy()
    next_page_token = eodag_args.pop("token", None)
    provider = eodag_args.get("provider")
    if not next_page_token or not provider:
        raise ValueError("Missing required token and federation backend for next page search.")
    search_plugin = next(dag._plugins_manager.get_search_plugins(provider=provider))
    next_page_token_key = getattr(search_plugin.config, "pagination", {}).get("next_page_token_key", "page")
    eodag_args.pop("count", None)
    search_result = SearchResult(
        [EOProduct(provider, {"id": "_"})] * int(eodag_args.get("limit", DEFAULT_LIMIT)),
        next_page_token=next_page_token,
        next_page_token_key=next_page_token_key,
        search_params=eodag_args,
        raise_errors=eodag_args.pop("raise_errors", None),
    )
    search_result._dag = dag
    try:
        search_result = next(search_result.next_page())
    except StopIteration:
        logger.info("StopIteration encountered during next page search.")
        search_result = SearchResult([])
    return search_result
