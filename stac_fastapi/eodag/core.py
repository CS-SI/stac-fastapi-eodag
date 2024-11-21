# -*- coding: utf-8 -*-
# Copyright 2023, CS GROUP - France, https://www.csgroup.eu/
#
# This file is part of EODAG project
#     https://www.github.com/CS-SI/EODAG
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

import logging
from datetime import datetime
from typing import Any, Optional, Set, Type, Union
from urllib.parse import unquote_plus, urljoin

import attr
import orjson
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
from pygeofilter.backends.cql2_json import to_cql2
from pygeofilter.parsers.cql2_text import parse as parse_cql2_text
from stac_fastapi.types.core import AsyncBaseCoreClient
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.rfc3339 import DateTimeType
from stac_fastapi.types.search import BaseSearchPostRequest
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes

from eodag.api.core import DEFAULT_ITEMS_PER_PAGE
from eodag.api.product._product import EOProduct
from eodag.utils import deepcopy
from eodag.utils.exceptions import NoMatchingProductType
from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.constants import ITEM_PROPERTIES_EXCLUDE
from stac_fastapi.eodag.eodag_types.search import EodagSearch
from stac_fastapi.eodag.errors import ResponseSearchError
from stac_fastapi.eodag.models.links import (
    CollectionLinks,
    ItemCollectionLinks,
    ItemLinks,
    PagingLinks,
)
from stac_fastapi.eodag.models.stac_metadata import CommonStacMetadata
from stac_fastapi.eodag.utils import dt_range_to_eodag, format_datetime_range

from stac_fastapi.eodag.utils import (
    dt_range_to_eodag,
    extract_cql2_properties,
    format_datetime_range,
    str2json,
)

NumType = Union[float, int]


logger = logging.getLogger()


@attr.s
class EodagCoreClient(AsyncBaseCoreClient):
    """"""

    stac_metadata_model: Type[BaseModel] = attr.ib(default=CommonStacMetadata)

    def _get_collection(
        self, product_type: dict[str, Any], request: Request
    ) -> Collection:
        """Convert a EODAG produt type to a STAC collection."""
        instruments = [
            instrument
            for instrument in (product_type.get("instrument") or "").split(",")
            if instrument
        ]

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
            description=product_type["abstract"],
            keywords=product_type["keywords"].split(","),
            license=product_type["license"],
            title=product_type["title"],
            extent=extent,
            summaries=summaries,
        )

        ext_stac_collection = deepcopy(
            request.app.state.ext_stac_collections.get(product_type["ID"], {})
        )

        collection["links"] = CollectionLinks(
            collection_id=collection["id"], request=request
        ).get_links(
            extra_links=product_type.get("links", [])
            + ext_stac_collection.get("links", [])
        )

        # merge "keywords" lists
        if "keywords" in ext_stac_collection:
            try:
                ext_stac_collection["keywords"] = [
                    k
                    for k in set(ext_stac_collection["keywords"] + collection["keywords"])
                    if k is not None
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

    async def _search_base(
        self, search_request: BaseSearchPostRequest, request: Request
    ) -> ItemCollection:
        settings = get_settings()

        geom = search_request.spatial_filter.wkt if search_request.spatial_filter else search_request.spatial_filter
        # get the extracted CQL2 properties dictionary if the CQL2 filter exists
        # TODO: find the right "search_request" class to remove the type hint
        query_params = extract_cql2_properties(search_request.filter) if search_request.filter is not None else {}

        base_args = {
            "items_per_page": search_request.limit,
            "geom": geom,
            "start": search_request.start_date.isoformat()
            if search_request.start_date
            else None,
            "end": search_request.end_date.isoformat()
            if search_request.end_date
            else None,
            **query_params
        }

        # EODAG search support a single collection
        if search_request.collections:
            base_args["productType"] = search_request.collections[0]

        # EODAG core search only support a single Id
        if search_request.ids:
            base_args["id"] = search_request.ids[0]

        search_result = request.app.state.dag.search(**base_args)

        if search_result.errors and not len(search_result):
            raise ResponseSearchError(search_result.errors, self.stac_metadata_model)

        request_json = await request.json() if request.method == "POST" else None

        features: list[Item] = []

        for product in search_result:
            feature = Item(
                assets={},
                id=product.properties["title"],
                geometry=product.geometry.__geo_interface__,
                bbox=product.geometry.bounds,
                collection=product.product_type,
                stac_version=self.stac_version,
            )

            stac_extensions: Set[str] = set()

            asset_proxy_url = (
                (
                    get_base_url(request)
                    + f"data/{product.provider}/{feature['collection']}/{feature['id']}" # type: ignore
                )
                if self.extension_is_enabled("DataDownload")
                else None
            )

            for k, v in product.assets.items():
                # TODO: download extension with origin link (make it optional ?)
                asset_model = self.stac_metadata_model.model_validate(v)
                stac_extensions.update(asset_model.get_conformance_classes())
                feature["assets"][k] = asset_model.model_dump(exclude_none=True)

                if asset_proxy_url:
                    origin = deepcopy(feature["assets"][k])
                    feature["assets"][k]["href"] = asset_proxy_url + "/" + k

                    if settings.keep_origin_url:
                        feature["assets"][k]["alternate"] = {"origin": origin}

            # TODO: remove downloadLink asset after EODAG assets rework
            if download_link := product.properties.get("downloadLink"):
                origin_href = download_link
                if asset_proxy_url:
                    download_link = asset_proxy_url + "/downloadLink"

                feature["assets"]["downloadLink"] = {
                    "title": "Download link",
                    "href": download_link,
                    # TODO: download link is not always a ZIP archive
                    "type": "application/zip",
                }

                if settings.keep_origin_url:
                    feature["assets"]["downloadLink"]["alternate"] = {
                        "origin": {
                            "title": "Origin asset link",
                            "href": origin_href,
                            # TODO: download link is not always a ZIP archive
                            "type": "application/zip",
                        },
                    }

            feature_model = self.stac_metadata_model.model_validate(
                {**product.properties, **{"federation:backends": [product.provider]}}
            )
            stac_extensions.update(feature_model.get_conformance_classes())
            feature["properties"] = feature_model.model_dump(
                exclude_none=True, exclude=ITEM_PROPERTIES_EXCLUDE
            )

            feature["stac_extensions"] = list(stac_extensions)

            feature["links"] = ItemLinks(
                collection_id=feature["collection"],
                item_id=feature["id"],
                request=request,
            ).get_links(extra_links=feature.get("links"), request_json=request_json)

            features.append(feature)

        collection = ItemCollection(features=features)

        # pagination
        next_page = None
        if search_request.page:
            number_returned = len(search_result)
            items_per_page = search_request.limit or DEFAULT_ITEMS_PER_PAGE
            if not search_result.number_matched or (
                (search_request.page - 1) * items_per_page + number_returned
                < search_result.number_matched
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
        """Get all collections from EODAG."""
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

        links = [
            {
                "rel": Relations.root.value,
                "type": MimeTypes.json,
                "href": base_url,
            },
            {
                "rel": Relations.parent.value,
                "type": MimeTypes.json,
                "href": base_url,
            },
            {
                "rel": Relations.self.value,
                "type": MimeTypes.json,
                "href": urljoin(base_url, "collections"),
            },
        ]
        return Collections(collections=collections or [], links=links)

    async def get_collection(
        self, collection_id: str, request: Request, **kwargs: Any
    ) -> Collection:
        """Get collection by id.

        Called with `GET /collections/{collection_id}`.

        Args:
            collection_id: ID of the collection.

        Returns:
            Collection.
        """
        product_type = next(
            (
                pt
                for pt in request.app.state.dag.list_product_types(fetch_providers=False)
                if pt["ID"] == collection_id
            ),
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
        """Get all items from a specific collection.

        Called with `GET /collections/{collection_id}/items`

        Args:
            collection_id: id of the collection.
            limit: number of items to return.
            token: pagination token.

        Returns:
            An ItemCollection.
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
        links = ItemCollectionLinks(
            collection_id=collection_id, request=request
        ).get_links(extra_links=item_collection["links"])
        item_collection["links"] = links
        return item_collection

    async def post_search(
        self, search_request: EodagSearch, request: Request, **kwargs: Any
    ) -> ItemCollection:
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
        intersects: Optional[str] = None,
        filter: Optional[str] = None,
        filter_lang: Optional[str] = "cql2-text",
        **kwargs: Any,
    ) -> ItemCollection:
        base_args = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "query": orjson.loads(unquote_plus(query)) if query else query,
            "page": page,
            "intersects": orjson.loads(unquote_plus(intersects))
            if intersects
            else intersects,
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
            raise HTTPException(
                status_code=400, detail=f"Invalid parameters provided {err}"
            ) from err

        return await self.post_search(search_request, request)

    async def get_item(
        self, item_id: str, collection_id: str, request: Request, **kwargs: Any
    ) -> Item:
        # If collection does not exist, NotFoundError wil be raised
        await self.get_collection(collection_id, request=request)

        search_request = self.post_request_model(
            ids=[item_id], collections=[collection_id], limit=1
        )
        item_collection = await self._search_base(search_request, request)
        if not item_collection["features"]:
            raise NotFoundError(
                f"Item {item_id} in Collection {collection_id} does not exist."
            )

        return Item(**item_collection["features"][0])

    async def download_item(
        self, item_id: str, collection_id: str, request: Request, **kwargs
    ):
        product: EOProduct
        product, _ = request.app.state.dag.search(
            {"productType": collection_id, "id": item_id}
        )[0]

        # when could this really happen ?
        if not product.downloader:
            download_plugin = request.app.state.dag._plugins_manager.get_download_plugin(
                product
            )
            auth_plugin = request.app.state.dag._plugins_manager.get_auth_plugin(
                download_plugin.provider
            )
            product.register_downloader(download_plugin, auth_plugin)

        # required for auth. Can be removed when EODAG implements the auth interface
        auth = (
            product.downloader_auth.authenticate()
            if product.downloader_auth is not None
            else product.downloader_auth
        )

        # can we make something more clean here ?
        download_stream_dict = product.downloader._stream_download_dict(
            product, auth=auth
        )

        return StreamingResponse(**download_stream_dict)
