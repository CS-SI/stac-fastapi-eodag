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
from datetime import datetime
from typing import Optional, Union
from urllib.parse import unquote_plus, urljoin
import attr

from eodag import EODataAccessGateway
from eodag.api.product._product import EOProduct
from eodag.api.core import DEFAULT_ITEMS_PER_PAGE, DEFAULT_PAGE
from fastapi.responses import StreamingResponse

import orjson
from pydantic import ValidationError

from fastapi import HTTPException, Request
from stac_fastapi.types.core import AsyncBaseCoreClient
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.stac import Collections, Collection, ItemCollection, Item

from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes

from stac_fastapi.eodag.models.links import (
    CollectionLinks,
    ItemCollectionLinks,
    ItemLinks,
    PagingLinks,
)

from stac_fastapi.eodag.eodag_types.search import EodagSearch
from stac_fastapi.eodag.models.item_properties import ItemProperties

NumType = Union[float, int]

dag = EODataAccessGateway()


@attr.s
class EodagCoreClient(AsyncBaseCoreClient):
    def _get_collection(self, product_type: dict, request: Request) -> Collection:
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

        collection["links"] = CollectionLinks(
            collection_id=collection["id"], request=request
        ).get_links(extra_links=product_type.get("links"), request_json=None)

        return collection

    async def _search_base(
        self, search_request: EodagSearch, request: Request
    ) -> ItemCollection:
        base_args = {
            "items_per_page": search_request.limit,
            "geom": search_request.spatial_filter,
            "start": search_request.start_date,
            "end": search_request.end_date,
        }

        # EODAG search support a single collection
        if search_request.collections:
            base_args["productType"] = search_request.collections[0]

        # EODAG core search only support a single Id
        if search_request.ids:
            base_args["id"] = search_request.ids[0]

        products: list[EOProduct]
        products, total = dag.search(**base_args)

        features: list[Item] = []
        for product in products:
            feature = Item(
                id=product.properties["title"],
                geometry=product.geometry.__geo_interface__,
                bbox=product.geometry.bounds,
                collection=product.product_type,
            )

            # TODO: assets with their extensions
            feature["stac_extensions"] = []
            # (feature["assets"], asset_extensions) = await ItemAssets().get_assets()

            (
                feature["properties"],
                props_extensions,
            ) = await ItemProperties(product_props=product.properties).get_properties()
            feature["stac_extensions"].extend(props_extensions)

            feature["links"] = await ItemLinks(
                collection_id=feature.get("collection"),
                item_id=feature.get("id"),
                request=request,
            ).get_links(extra_links=feature.get("links"))

            features.append(feature)

        itemcollection = ItemCollection(type="FeatureCollection", features=features)

        # pagination
        next_page = None
        number_returned = len(products)
        page = search_request.page or DEFAULT_PAGE
        items_per_page = search_request.limit or DEFAULT_ITEMS_PER_PAGE

        if (page - 1) * items_per_page + number_returned < total:
            next_page = page + 1

        itemcollection["links"] = await PagingLinks(
            request=request,
            next=next_page,
            # prev="prev",
        ).get_links()
        return itemcollection

    async def all_collections(self, request: Request, **kwargs) -> Collections:
        base_url = get_base_url(request)

        product_types = dag.list_product_types()

        collections: list[Collection] = []

        for pt in product_types:
            collection = self._get_collection(pt, request)
            if collection is not None:
                collections.append(collection)

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
        self, collection_id: str, request: Request, **kwargs
    ) -> Collection:
        product_type = next(
            (pt for pt in dag.list_product_types() if pt["ID"] == collection_id), None
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
        **kwargs,
    ) -> ItemCollection:
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

        search_request = self.post_request_model(
            **clean,
        )
        item_collection = await self._search_base(search_request, request)
        links = await ItemCollectionLinks(
            collection_id=collection_id, request=request
        ).get_links(extra_links=item_collection["links"])
        item_collection["links"] = links
        return item_collection

    async def post_search(
        self, search_request: EodagSearch, request: Request, **kwargs
    ) -> ItemCollection:
        return await self._search_base(search_request, request)

    async def get_search(
        self,
        request: Request,
        collections: Optional[list[str]] = None,
        ids: Optional[list[str]] = None,
        bbox: Optional[list[NumType]] = None,
        datetime: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
        query: Optional[str] = None,
        page: Optional[str] = None,
        intersects: Optional[str] = None,
        **kwargs,
    ) -> ItemCollection:
        base_args = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "datetime": datetime,
            "query": orjson.loads(unquote_plus(query)) if query else query,
            "page": page,
            "intersects": orjson.loads(unquote_plus(intersects))
            if intersects
            else intersects,
        }

        # Remove None values from dict
        clean = {}
        for k, v in base_args.items():
            if v is not None and v != []:
                clean[k] = v

        try:
            search_request = self.post_request_model(**clean)
        except ValidationError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid parameters provided {e}"
            )

        return await self.post_search(search_request, request)

    async def get_item(
        self, item_id: str, collection_id: str, request: Request, **kwargs
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
        product, _ = dag.search({
            "productType": collection_id,
            "id": item_id
        })[0]

        # when could this really happen ? 
        if not product.downloader:
            download_plugin = dag._plugins_manager.get_download_plugin(product)
            auth_plugin = dag._plugins_manager.get_auth_plugin(
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
