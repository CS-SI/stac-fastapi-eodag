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

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote_plus, urljoin

import attr
import orjson
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from pydantic.alias_generators import to_camel, to_snake
from pydantic_core import InitErrorDetails, PydanticCustomError
from pygeofilter.backends.cql2_json import to_cql2
from pygeofilter.parsers.cql2_json import parse as parse_json
from pygeofilter.parsers.cql2_text import parse as parse_cql2_text
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.search import BaseSearchPostRequest
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes

from eodag import SearchResult
from eodag.api.core import DEFAULT_ITEMS_PER_PAGE
from eodag.utils import deepcopy
from eodag.utils.exceptions import NoMatchingProductType
from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.cql_evaluate import EodagEvaluator
from stac_fastapi.eodag.errors import ResponseSearchError
from stac_fastapi.eodag.landing_page import CustomCoreClient
from stac_fastapi.eodag.models.links import (
    CollectionLinks,
    ItemCollectionLinks,
    PagingLinks,
)
from stac_fastapi.eodag.models.stac_metadata import (
    CommonStacMetadata,
    create_stac_item,
    get_sortby_to_post,
)
from stac_fastapi.eodag.utils import (
    dt_range_to_eodag,
    format_datetime_range,
    is_dict_str_any,
    str2json,
)

if TYPE_CHECKING:
    from typing import Optional, Union

    from fastapi import Request
    from pydantic import BaseModel
    from stac_fastapi.types.rfc3339 import DateTimeType

    from eodag.api.product._product import EOProduct

    NumType = Union[float, int]


logger = logging.getLogger()


@attr.s
class EodagCoreClient(CustomCoreClient):
    """"""

    post_request_model: type[BaseModel] = attr.ib(default=BaseSearchPostRequest)
    stac_metadata_model: type[CommonStacMetadata] = attr.ib(default=CommonStacMetadata)

    def _get_collection(self, product_type: dict[str, Any], request: Request) -> Collection:
        """Convert a EODAG produt type to a STAC collection."""
        instruments = [instrument for instrument in (product_type.get("instrument") or "").split(",") if instrument]

        summaries = {
            key: value
            for key, value in {
                "platform": product_type.get("platformSerialIdentifier"),
                "constellation": product_type.get("platform"),
                "processing:level": product_type.get("processingLevel"),
                "instruments": instruments,
            }.items()
            if value
        }

        extent = {
            "spatial": {"bbox": [[-180.0, -90.0, 180.0, 90.0]]},
            "temporal": {
                "interval": [
                    [
                        product_type.get("missionStartDate"),
                        product_type.get("missionEndDate"),
                    ]
                ]
            },
        }

        collection = Collection(
            id=product_type["ID"],
            description=product_type.get("abstract", ""),
            keywords=product_type.get("keywords", "").split(","),
            license=product_type.get("license", "other"),
            title=product_type.get("title", product_type["ID"]),
            extent=extent,
            summaries=summaries,
        )

        ext_stac_collection = deepcopy(request.app.state.ext_stac_collections.get(product_type["ID"], {}))

        collection["links"] = CollectionLinks(collection_id=collection["id"], request=request).get_links(
            extra_links=product_type.get("links", []) + ext_stac_collection.get("links", [])
        )

        # merge "keywords" lists
        if "keywords" in ext_stac_collection:
            try:
                ext_stac_collection["keywords"] = [
                    k for k in set(ext_stac_collection["keywords"] + collection["keywords"]) if k is not None
                ]
            except TypeError as e:
                logger.warning(
                    "Could not merge keywords from external collection for",
                    f"{product_type['ID']}: {str(e)}",
                )

        # merge providers
        if "providers" in ext_stac_collection:
            ext_stac_collection["providers"] += collection["providers"]

        collection.update(ext_stac_collection)

        return collection

    async def _search_base(self, search_request: BaseSearchPostRequest, request: Request) -> ItemCollection:
        # check if the collection exists
        if search_request.collections:
            all_pt = request.app.state.dag.list_product_types(fetch_providers=False)
            # only check the first collection (EODAG search only support a single collection)
            existing_pt = [pt for pt in all_pt if pt["ID"] == search_request.collections[0]]
            if not existing_pt:
                raise NoMatchingProductType(f"Collection {search_request.collections[0]} does not exist.")

        # get products by ids
        if search_request.ids:
            search_result = SearchResult([])
            ids = search_request.ids
            for item_id in ids:
                search_request.ids = [item_id]
                base_args = prepare_search_base_args(search_request=search_request, model=self.stac_metadata_model)
                search_result.extend(request.app.state.dag.search(**base_args))
            search_result.number_matched = len(search_result)
        else:
            # search without ids
            base_args = prepare_search_base_args(search_request=search_request, model=self.stac_metadata_model)
            search_result = request.app.state.dag.search(**base_args)

        if search_result.errors and not len(search_result):
            raise ResponseSearchError(search_result.errors, self.stac_metadata_model)

        request_json = await request.json() if request.method == "POST" else None

        features: list[Item] = []

        for product in search_result:
            feature = create_stac_item(
                product, self.stac_metadata_model, self.extension_is_enabled, request, request_json
            )
            features.append(feature)

        collection = ItemCollection(
            type="FeatureCollection",
            features=features,
            numberMatched=search_result.number_matched,
            numberReturned=len(features),
        )

        # pagination
        next_page = None
        if search_request.page:
            number_returned = len(search_result)
            items_per_page = search_request.limit or DEFAULT_ITEMS_PER_PAGE
            if not search_result.number_matched or (
                (search_request.page - 1) * items_per_page + number_returned < search_result.number_matched
            ):
                next_page = search_request.page + 1

        collection["links"] = PagingLinks(
            request=request,
            next=next_page,
        ).get_links(request_json=request_json)
        return collection

    async def all_collections(
        self,
        request: Request,
        bbox: Optional[list[NumType]] = None,
        datetime: Optional[DateTimeType] = None,
        limit: Optional[int] = None,
        q: Optional[str] = None,
    ) -> Collections:
        """
        Get all collections from EODAG.

        :param request: The request object.
        :param bbox: Bounding box to filter the collections.
        :param datetime: Date and time range to filter the collections.
        :param limit: Maximum number of collections to return.
        :param q: Query string to filter the collections.
        :returns: All collections.
        :raises HTTPException: If the unsupported bbox parameter is provided.
        """
        base_url = get_base_url(request)

        if bbox:
            raise HTTPException(
                status_code=400,
                detail="bbox parameter is not yet supported in /collections.",
            )

        all_pt = request.app.state.dag.list_product_types(fetch_providers=False)

        if any((q, datetime)):
            start, end = dt_range_to_eodag(datetime)

            try:
                guessed_product_types = request.app.state.dag.guess_product_type(
                    free_text=q, missionStartDate=start, missionEndDate=end
                )
            except NoMatchingProductType:
                product_types = []
            else:
                product_types = [pt for pt in all_pt if pt["ID"] in guessed_product_types]
        else:
            product_types = all_pt

        collections = [self._get_collection(pt, request) for pt in product_types[:limit]]
        stac_fastapi_title = get_settings().stac_fastapi_title
        links = [
            {"rel": Relations.root.value, "type": MimeTypes.json, "href": base_url, "title": f"{stac_fastapi_title}"},
            {"rel": Relations.parent.value, "type": MimeTypes.json, "href": base_url, "title": f"{stac_fastapi_title}"},
            {
                "rel": Relations.self.value,
                "type": MimeTypes.json,
                "href": urljoin(base_url, "collections"),
                "title": "Collection",
            },
        ]
        return Collections(collections=collections or [], links=links)

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
        product_type = next(
            (pt for pt in request.app.state.dag.list_product_types(fetch_providers=False) if pt["ID"] == collection_id),
            None,
        )
        if product_type is None:
            raise NotFoundError(f"Collection {collection_id} does not exist.")

        return self._get_collection(product_type, request)

    async def item_collection(
        self,
        collection_id: str,
        request: Request,
        bbox: Optional[list[NumType]] = None,
        datetime: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
        page: Optional[str] = None,
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
        :param page: Page token for pagination.
        :param kwargs: Additional arguments.
        :returns: An ItemCollection.
        :raises NotFoundError: If the collection does not exist.
        """
        # If collection does not exist, NotFoundError wil be raised
        await self.get_collection(collection_id, request=request)

        base_args = {
            "collections": [collection_id],
            "bbox": bbox,
            "datetime": datetime,
            "limit": limit,
            "page": page,
        }

        clean = {}
        for k, v in base_args.items():
            if v is not None and v != []:
                clean[k] = v

        search_request = self.post_request_model.model_validate(clean)
        item_collection = await self._search_base(search_request, request)
        links = ItemCollectionLinks(collection_id=collection_id, request=request).get_links(
            extra_links=item_collection["links"]
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
        datetime: Optional[DateTimeType] = None,
        limit: Optional[int] = None,
        query: Optional[str] = None,
        page: Optional[str] = None,
        sortby: Optional[list[str]] = None,
        intersects: Optional[str] = None,
        filter: Optional[str] = None,
        filter_lang: Optional[str] = "cql2-text",
        **kwargs: Any,
    ) -> ItemCollection:
        """
        Handles the GET search request for STAC items.

        :param request: The request object.
        :param collections: List of collection IDs to include in the search.
        :param ids: List of item IDs to include in the search.
        :param bbox: Bounding box to filter the search.
        :param datetime: Date and time range to filter the search.
        :param limit: Maximum number of items to return.
        :param query: Query string to filter the search.
        :param page: Page token for pagination.
        :param sortby: List of fields to sort the results by.
        :param intersects: GeoJSON geometry to filter the search.
        :param filter: CQL filter to apply to the search.
        :param filter_lang: Language of the filter (default is "cql2-text").
        :param kwargs: Additional arguments.
        :returns: Found items.
        :raises HTTPException: If the provided parameters are invalid.
        """
        base_args = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "query": orjson.loads(unquote_plus(query)) if query else query,
            "page": page,
            "sortby": get_sortby_to_post(sortby),
            "intersects": orjson.loads(unquote_plus(intersects)) if intersects else intersects,
        }

        if datetime:
            base_args["datetime"] = format_datetime_range(datetime)

        if filter:
            if filter_lang == "cql2-text":
                ast = parse_cql2_text(filter)
                base_args["filter"] = str2json("filter", to_cql2(ast))  # type: ignore
                base_args["filter-lang"] = "cql2-json"
            elif filter_lang == "cql-json":
                base_args["filter"] = str2json(filter)

        # Remove None values from dict
        clean = {}
        for k, v in base_args.items():
            if v is not None and v != []:
                clean[k] = v

        try:
            search_request = self.post_request_model(**clean)
        except ValidationError as err:
            raise HTTPException(status_code=400, detail=f"Invalid parameters provided {err}") from err

        return await self.post_search(search_request, request)

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
        # If collection does not exist, NotFoundError wil be raised
        await self.get_collection(collection_id, request=request)

        search_request = self.post_request_model(ids=[item_id], collections=[collection_id], limit=1)
        item_collection = await self._search_base(search_request, request)
        if not item_collection["features"]:
            raise NotFoundError(f"Item {item_id} in Collection {collection_id} does not exist.")

        return Item(**item_collection["features"][0])

    async def download_item(self, item_id: str, collection_id: str, request: Request, **kwargs) -> StreamingResponse:
        """
        Download item by ID.

        :param item_id: ID of the item.
        :param collection_id: ID of the collection.
        :param request: The request object.
        :param kwargs: Additional arguments.
        :returns: Streaming response for the item download.
        """
        product: EOProduct
        product, _ = request.app.state.dag.search({"productType": collection_id, "id": item_id})[0]

        # when could this really happen ?
        if not product.downloader:
            download_plugin = request.app.state.dag._plugins_manager.get_download_plugin(product)
            auth_plugin = request.app.state.dag._plugins_manager.get_auth_plugin(download_plugin.provider)
            product.register_downloader(download_plugin, auth_plugin)

        # required for auth. Can be removed when EODAG implements the auth interface
        auth = (
            product.downloader_auth.authenticate() if product.downloader_auth is not None else product.downloader_auth
        )

        if product.downloader is None:
            raise HTTPException(status_code=500, detail="No downloader found for this product")
        # can we make something more clean here ?
        download_stream_dict = product.downloader._stream_download_dict(product, auth=auth)

        return StreamingResponse(
            content=download_stream_dict.content,
            headers=download_stream_dict.headers,
            media_type=download_stream_dict.media_type,
        )


def prepare_search_base_args(search_request: BaseSearchPostRequest, model: type[CommonStacMetadata]) -> dict[str, Any]:
    """Prepare arguments for an eodag search based on a search request

    :param search_request: the search request
    :param model: the model used to validate stac metadata
    :returns: a dictionnary containing arguments for the eodag search
    """
    base_args = (
        {
            "page": search_request.page,
            "items_per_page": search_request.limit,
            "raise_errors": False,
            "count": True,
        }
        if search_request.ids is None
        else {}
    )

    if search_request.spatial_filter is not None:
        base_args["geom"] = search_request.spatial_filter.wkt
    # Also check datetime to bypass persistent dates between searches
    # until https://github.com/stac-utils/stac-pydantic/pull/171 is merged
    if search_request.datetime is not None and search_request.start_date is not None:
        base_args["start"] = search_request.start_date.isoformat()
    if search_request.datetime is not None and search_request.end_date is not None:
        base_args["end"] = search_request.end_date.isoformat()

    # parse "sortby" search request attribute if it exists to make it work for an eodag search
    sort_by = {}
    if sortby := getattr(search_request, "sortby", None):
        sort_by_special_fields = {
            "start": "startTimeFromAscendingNode",
            "end": "completionTimeFromAscendingNode",
        }
        param_tuples = []
        for param in sortby:
            dumped_param = param.model_dump(mode="json")
            param_tuples.append(
                (
                    sort_by_special_fields.get(
                        to_camel(to_snake(model.to_eodag(dumped_param["field"]))),
                        to_camel(to_snake(model.to_eodag(dumped_param["field"]))),
                    ),
                    dumped_param["direction"],
                )
            )
        sort_by["sort_by"] = param_tuples

    eodag_query = {}
    if query_attr := getattr(search_request, "query", None):
        parsed_query = parse_query(query_attr)
        eodag_query = {model.to_eodag(k): v for k, v in parsed_query.items()}

    # get the extracted CQL2 properties dictionary if the CQL2 filter exists
    eodag_filter = {}
    if f := getattr(search_request, "filter", None):
        parsed_filter = parse_cql2(f)
        eodag_filter = {model.to_eodag(k): v for k, v in parsed_filter.items()}

    # EODAG search support a single collection
    if search_request.collections:
        base_args["productType"] = search_request.collections[0]

    # handle only one id from here (pre-filtered in _search_base)
    if search_request.ids:
        base_args["id"] = search_request.ids[0]

    # merge all eodag search arguments
    base_args = base_args | sort_by | eodag_filter | eodag_query

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
                type=PydanticCustomError("invalid_filter", error_message),  # type: ignore
                loc=("filter",),
            )
        )

    errors: list[InitErrorDetails] = []
    try:
        parsing_result = EodagEvaluator().evaluate(parse_json(filter_))  # type: ignore
    except (ValueError, NotImplementedError) as e:
        add_error(str(e))
        raise ValidationError.from_exception_data(title="EODAGSearch", line_errors=errors) from e

    if not is_dict_str_any(parsing_result):
        add_error("The parsed filter is not a proper dictionary")
        raise ValidationError.from_exception_data(title="EODAGSearch", line_errors=errors)

    cql_args: dict[str, Any] = cast(dict[str, Any], parsing_result)

    invalid_keys = {
        "collections": 'Use "collection" instead of "collections"',
        "ids": 'Use "id" instead of "ids"',
    }
    for k, m in invalid_keys.items():
        if k in cql_args:
            add_error(m)

    if errors:
        raise ValidationError.from_exception_data(title="EODAGSearch", line_errors=errors)

    return cql_args
