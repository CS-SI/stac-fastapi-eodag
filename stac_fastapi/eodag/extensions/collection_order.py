"""Data-download extension."""

import logging
from typing import (
    Annotated,
    List,
    Type,
    cast,
)

import attr
from eodag.api.core import EODataAccessGateway
from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import OFFLINE_STATUS
from fastapi import APIRouter, FastAPI, Path, Query, Request
from pydantic import BaseModel
from stac_fastapi.api.errors import NotFoundError
from stac_fastapi.api.routes import create_async_endpoint
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest
from stac_fastapi.types.stac import Item

from stac_fastapi.eodag.errors import (
    MisconfiguredError,
)
from stac_fastapi.eodag.models.stac_metadata import (
    CommonStacMetadata,
    create_stac_item,
)

logger = logging.getLogger(__name__)

@attr.s
class BaseCollectionOrderClient():
    """Defines a pattern for implementing the data order extension."""
    stac_metadata_model: Type[BaseModel] = attr.ib(default=CommonStacMetadata)
    extensions: List[ApiExtension] = attr.ib(default=[])

    def extension_is_enabled(self, extension: str) -> bool:
        """Check if an api extension is enabled."""
        return any(type(ext).__name__ == extension for ext in self.extensions)

    def order_data(
        self,
        federation_backend: str,
        collection_id: str,
        dc_qs: str,
        request: Request,
    ) -> Item:
        """Download an asset"""

        dag = cast(EODataAccessGateway, request.app.state.dag)  # type: ignore

        search_results = dag.search(
            id="fake_id", productType=collection_id, provider=federation_backend, _dc_qs=dc_qs
        )
        if len(search_results) > 0:
            product = cast(EOProduct, search_results[0])

        else:
            raise NotFoundError(
                f"Could not find any item in {collection_id} collection"
                f" for backend {federation_backend}.",
            )

        if not getattr(product.downloader, "order_download", None):
            raise MisconfiguredError("Product downloader must have a the order method")

        auth = product.downloader_auth.authenticate() if product.downloader_auth else None

        if product.properties.get("orderLink") is None or product.properties.get("storageStatus") != OFFLINE_STATUS:
            raise NotFoundError(
                "Product is not orderable. Please download it directly.",
            )

        if product.properties.get("orderStatus"):
            raise NotFoundError(
                "Product has been ordered previously. Please request the polling endpoint before download it."
            )

        logger.debug("Order product")
        _ = product.downloader.order_download(
            product=product, auth=auth
        )

        if product.properties.get("orderId") is None:
            raise NotFoundError(
                "Download order failed. It can be due to a lack of product found, so you "
                f"may change 'dc_qs' argument. The one used for this order was: {dc_qs}"
            )

        return create_stac_item(
            product,
            self.stac_metadata_model,
            self.extension_is_enabled,
            request
        )


@attr.s
class DataOrderUri(APIRequest):
    """Download data."""

    federation_backend: Annotated[str, Path(description="Federation backend name")] = (
        attr.ib()
    )
    collection_id: Annotated[str, Path(description="Collection ID")] = attr.ib()
    dc_qs: Annotated[str, Query()] = attr.ib()


@attr.s
class CollectionOrderExtension(ApiExtension):
    """Collection Order extension.

    The download-data extension allow to download data directly through the EODAG STAC
    server.
    Attributes:
        GET /data/{federation_backend}/{collection_id}/{item_id}/{asset_id}
    """

    client: BaseCollectionOrderClient = attr.ib(factory=BaseCollectionOrderClient)
    router: APIRouter = attr.ib(factory=APIRouter)

    def register(self, app: FastAPI) -> None:
        """Register the extension with a FastAPI application.

        Args:
            app: target FastAPI application.

        Returns:
            None
        """
        self.router.prefix = app.state.router_prefix
        self.router.add_api_route(
            name="Order collection",
            path="/collections/{collection_id}/{federation_backend}/orders",
            methods=["POST"],
            responses={
                200: {
                    "content": {
                        "application/geo+json": {},
                    },
                }
            },
            endpoint=create_async_endpoint(self.client.order_data, DataOrderUri),
        )
        app.include_router(self.router, tags=["Collection order"])
