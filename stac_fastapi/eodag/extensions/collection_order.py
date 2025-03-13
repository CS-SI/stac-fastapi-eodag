# -*- coding: utf-8 -*-
# Copyright 2025, CS GROUP - France, https://www.cs-soprasteria.com
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
# limitations under the License.
"""Collection-order extension."""

import logging
from typing import (
    Annotated,
    cast,
)

import attr
from eodag.api.core import EODataAccessGateway
from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import OFFLINE_STATUS
from fastapi import APIRouter, Depends, FastAPI, Path, Request
from pydantic import BaseModel, ConfigDict
from stac_fastapi.api.errors import NotFoundError
from stac_fastapi.api.routes import _wrap_response, sync_to_async
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest
from stac_fastapi.types.stac import Item

from stac_fastapi.eodag.models.stac_metadata import (
    CommonStacMetadata,
    create_stac_item,
)

logger = logging.getLogger(__name__)


class CollectionOrderBody(BaseModel):
    """Collection order request body."""

    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{"date": "string", "variable": "string"}]})


@attr.s
class BaseCollectionOrderClient:
    """Defines a pattern for implementing the collection order extension."""

    stac_metadata_model: type[CommonStacMetadata] = attr.ib(default=CommonStacMetadata)
    extensions: list[ApiExtension] = attr.ib(default=[])

    def extension_is_enabled(self, extension: str) -> bool:
        """Check if an api extension is enabled."""
        return any(type(ext).__name__ == extension for ext in self.extensions)

    def order_collection(
        self,
        federation_backend: str,
        collection_id: str,
        request: Request,
        request_body: CollectionOrderBody,
    ) -> Item:
        """Order a product with its collection id and a fake id"""

        dag = cast(EODataAccessGateway, request.app.state.dag)

        search_results = dag.search(productType=collection_id, provider=federation_backend, **request_body.model_dump())
        if len(search_results) > 0:
            product = cast(EOProduct, search_results[0])

        else:
            raise NotFoundError(
                f"Could not find any item in {collection_id} collection for backend {federation_backend}.",
            )

        auth = product.downloader_auth.authenticate() if product.downloader_auth else None

        if product.properties.get("orderLink") is None or product.properties.get("storageStatus") != OFFLINE_STATUS:
            raise NotFoundError(
                "Product is not orderable. Please download it directly.",
            )

        if product.properties.get("orderStatus"):
            raise NotFoundError("Product has already been ordered and polled, it can be directly downloaded.")

        raise_error = False
        if product.downloader is None:
            logger.error("No downloader available for %s", product)
            raise_error = True
        elif not hasattr(product.downloader, "_order"):
            logger.error("No _order method available for %s of %s", product.downloader, product)
            raise_error = True
        else:
            logger.debug("Order product")
            product.downloader.order(product=product, auth=auth, timeout=-1)

        if raise_error or product.properties.get("orderId") is None:
            raise NotFoundError(
                "Download order failed. It can be due to a lack of product found, so you "
                "may change the body of the request."
            )

        return create_stac_item(product, self.stac_metadata_model, self.extension_is_enabled, request)


@attr.s
class CollectionOrderUri(APIRequest):
    """Order collection."""

    federation_backend: Annotated[str, Path(description="Federation backend name")] = attr.ib()
    collection_id: Annotated[str, Path(description="Collection ID")] = attr.ib()


@attr.s
class CollectionOrderExtension(ApiExtension):
    """Collection Order extension.

    The order-collection extension allow to order a collection directly through the EODAG STAC server.

    Usage:
    ------

        ``POST /order/{federation_backend}/{collection_id}``
    """

    client: BaseCollectionOrderClient = attr.ib(factory=BaseCollectionOrderClient)
    router: APIRouter = attr.ib(factory=APIRouter)

    def register(self, app: FastAPI) -> None:
        """
        Register the extension with a FastAPI application.

        :param app: Target FastAPI application.
        :returns: None
        """
        func = sync_to_async(self.client.order_collection)

        async def _retrieve_endpoint(
            request: Request,
            request_data: CollectionOrderBody,
            request_path: CollectionOrderUri = Depends(),  # noqa: B008
        ):
            """Retrieve endpoint."""
            return _wrap_response(await func(request=request, request_body=request_data, **request_path.kwargs()))

        self.router.prefix = app.state.router_prefix
        self.router.add_api_route(
            name="Order collection",
            path="/order/{federation_backend}/{collection_id}",
            methods=["POST"],
            responses={
                200: {
                    "content": {
                        "application/geo+json": {},
                    },
                }
            },
            endpoint=_retrieve_endpoint,
        )
        app.include_router(self.router, tags=["Collection order"])
