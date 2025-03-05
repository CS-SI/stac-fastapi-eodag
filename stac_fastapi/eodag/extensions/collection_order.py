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
from urllib.parse import quote_plus

import attr
import orjson
from eodag.api.core import EODataAccessGateway
from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import (
    DEFAULT_GEOMETRY,
    OFFLINE_STATUS,
    STAGING_STATUS,
)
from fastapi import APIRouter, Depends, FastAPI, Path, Request
from pydantic import BaseModel, ConfigDict
from stac_fastapi.api.errors import NotFoundError
from stac_fastapi.api.routes import _wrap_response, create_async_endpoint, sync_to_async
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest
from stac_fastapi.types.stac import Item

from stac_fastapi.eodag.errors import (
    DownloadError,
    MisconfiguredError,
    NoMatchingProductType,
    NotAvailableError,
    ValidationError,
)
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
        query_body: CollectionOrderBody,
    ) -> Item:
        """Order a product with its collection id and a fake id"""

        dag = cast(EODataAccessGateway, request.app.state.dag)

        encoded_dc_qs = quote_plus(orjson.dumps(query_body.model_dump()))

        search_results = dag.search(
            id="fake_id", productType=collection_id, provider=federation_backend, _dc_qs=encoded_dc_qs
        )
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
            raise NotFoundError(
                "Product has already been ordered and polled, it can be directly downloaded."
            )

        raise_error = False
        if product.downloader is None:
            logger.error("No downloader available for %s", product)
            raise_error = True
        elif not hasattr(product.downloader, "_order"):
            logger.error("No _order method available for %s of %s", product.downloader, product)
            raise_error = True
        else:
            logger.debug("Order product")
            _ = product.downloader._order(product=product, auth=auth)

        if raise_error or product.properties.get("orderId") is None:
            raise NotFoundError(
                "Download order failed. It can be due to a lack of product found, so you "
                "may change the body of the request."
            )

        return create_stac_item(product, self.stac_metadata_model, self.extension_is_enabled, request)


    def poll_collection(
        self,
        federation_backend: str,
        collection_id: str,
        order_id: str,
        request: Request,
    ) -> Item:
        """Poll a collection previously ordered"""

        dag = cast(EODataAccessGateway, request.app.state.dag)  # type: ignore

        # check if the collection is known
        try:
            product_type = dag.get_product_type_from_alias(collection_id)
        except NoMatchingProductType as e:
            raise NotFoundError(e) from e

        # set fake properties to make EOProduct initialization possible
        # among these properties, "title" is set to deal with error while polling
        fake_properties = {
            "id": order_id,
            "title": order_id,
            "geometry": DEFAULT_GEOMETRY,
        }

        # "productType" kwarg must be set to convert the product to a STAC item
        product = EOProduct(federation_backend, fake_properties, productType=product_type)
        product.downloader = dag._plugins_manager.get_download_plugin(product)
        # orderLink is set to auth provider conf matching url to create its auth plugin
        product.properties["orderLink"] = product.properties["orderStatusLink"] = product.downloader.config.order_on_response["metadata_mapping"]["orderStatusLink"].format(orderId=order_id)
        search_link = {
            "searchLink": product.downloader.config.order_on_response["metadata_mapping"]["searchLink"].format(orderId=order_id)
        } if product.downloader.config.order_on_response["metadata_mapping"].get("searchLink") else {}
        product.properties = {**product.properties, **search_link}
        product.downloader_auth = dag._plugins_manager.get_auth_plugin(product.downloader, product)

        if not getattr(product.downloader, "_order_status", None):
            raise MisconfiguredError("Product downloader must have the order status request method")

        auth = product.downloader_auth.authenticate() if product.downloader_auth else None

        logger.debug("Poll product")
        try:
            _ = product.downloader._order_status(
                product=product, auth=auth
            )
        # when a NotAvailableError is catched, it means the product is not ready and still needs to be polled
        except NotAvailableError:
            product.properties["storageStatus"] = STAGING_STATUS
        except Exception as e:
            if (
                (isinstance(e, DownloadError) or isinstance(e, ValidationError))
                and "order status could not be checked" in e.args[0]
            ):
                raise NotFoundError(
                    f"Item {order_id} does not exist. Please order it first"
                ) from e
            raise NotFoundError(e) from e

        return create_stac_item(
            product,
            self.stac_metadata_model,
            self.extension_is_enabled,
            request
        )


@attr.s
class CollectionOrderUri(APIRequest):
    """Order collection."""

    federation_backend: Annotated[str, Path(description="Federation backend name")] = attr.ib()
    collection_id: Annotated[str, Path(description="Collection ID")] = attr.ib()


@attr.s
class CollectionPollingUri(APIRequest):
    """Polling collection."""

    federation_backend: Annotated[str, Path(description="Federation backend name")] = attr.ib()
    collection_id: Annotated[str, Path(description="Collection ID")] = attr.ib()
    order_id: Annotated[str, Path(description="Order ID")] = attr.ib()


@attr.s
class CollectionOrderExtension(ApiExtension):
    """Collection Order extension.

    The order-collection extension allow to order and poll a collection directly through the EODAG STAC
    server.

    Usage:
    ------

        ``POST /collections/{collection_id}/{federation_backend}/retrieve``
        ``GET /collections/{collection_id}/{federation_backend}/retrieve/{order_id}``
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
            request_data: CollectionOrderBody = CollectionOrderBody(),
            request_path: CollectionOrderUri = Depends()
        ):
            """Create "retrieve" endpoint."""
            return _wrap_response(await func(request=request, query_body=request_data, **request_path.kwargs()))

        self.router.prefix = app.state.router_prefix
        self.router.add_api_route(
            name="Order collection",
            path="/collections/{collection_id}/{federation_backend}/retrieve",
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
        self.router.add_api_route(
            name="Poll collection",
            path="/collections/{collection_id}/{federation_backend}/retrieve/{order_id}",
            methods=["GET"],
            responses={
                200: {
                    "content": {
                        "application/geo+json": {},
                    },
                }
            },
            endpoint=create_async_endpoint(self.client.poll_collection, CollectionPollingUri),
        )
        app.include_router(self.router, tags=["Collection order"])
