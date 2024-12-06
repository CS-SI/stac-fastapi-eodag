"""Data-download extension."""

import logging
from typing import (
    Annotated,
    cast,
)

import attr
from eodag.api.core import EODataAccessGateway
from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import (
    NOT_AVAILABLE,
    OFFLINE_STATUS,
    ONLINE_STATUS,
    STAGING_STATUS,
)
from fastapi import APIRouter, FastAPI, Path, Query, Request
from fastapi.responses import ORJSONResponse
from stac_fastapi.api.errors import NotFoundError
from stac_fastapi.api.routes import create_async_endpoint
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest
from stac_fastapi.types.stac import Item

from stac_fastapi.eodag.errors import (
    MisconfiguredError,
)
from stac_fastapi.eodag.models.stac_metadata import STATUS_STAC_MATCHING

logger = logging.getLogger(__name__)


class BaseCollectionOrderClient():
    """Defines a pattern for implementing the data order extension."""

    def order_data(
        self,
        federation_backend: str,
        collection_id: str,
        dc_qs: str,
        request: Request,
    ) -> ORJSONResponse:
        """Download an asset"""

        # arguments = dict(request.query_params)
        # dc_qs: Dict[Literal["dc_qs"], str] = {"dc_qs": arguments["dc_qs"]} if arguments.get("dc_qs", None) else {}

        dag = cast(EODataAccessGateway, request.app.state.dag)  # type: ignore

        search_results = dag.search(
            id="fake_id", productType=collection_id, provider=federation_backend, _dc_qs=dc_qs
        )
        if len(search_results) > 0:
            product = cast(EOProduct, search_results[0])

        else:
            raise NotFoundError(
                f"Could not find any item in {collection_id} collection"
                # f"Could not find {item_id} item in {collection_id} collection",
                f" for backend {federation_backend}.",
            )

        if not getattr(product.downloader, "order_download", None):
            raise MisconfiguredError("Product downloader must have a the order method")

        auth = product.downloader_auth.authenticate() if product.downloader_auth else None

        if product.properties.get("orderLink") is None or product.properties.get("storageStatus") != OFFLINE_STATUS:
            raise NotFoundError(
                "Product is not orderable. Please download it directly.",
            )

        if product.properties.get("orderStatus"): # mettre s'il y a un orderId
            return ORJSONResponse(
                status_code=404,
                content={
                    "description": "Product has been ordered previously. Please request the polling endpoint before download it.",
                },
            )

        # if product.properties.get("storageStatus") != ONLINE_STATUS and hasattr( # pas nessaire car le but c'est d'aller à l'endpoint de polling si déjà ordered
        #     product.downloader, "order_response_process"
        # ):
        #     # update product (including orderStatusLink) if product was previously ordered
        #     logger.debug("Use given download query arguments to parse order link")
        #     response = Mock(spec=RequestsResponse)
        #     response.status_code = 200
        #     response.json.return_value = product.search_kwargs # faire un {} au cas où ? # query_args
        #     response.headers = {}
        #     product.downloader.order_response_process(response, product)

        if (
            product.properties.get("storageStatus") == OFFLINE_STATUS
            and NOT_AVAILABLE not in product.properties.get("orderStatusLink", NOT_AVAILABLE)
        ):
            product.properties["storageStatus"] = STAGING_STATUS # vraiment utile ? car on met à staging au début de order_download()

        # if (
        #     # product.properties.get("storageStatus") != ONLINE_STATUS
        #     # and NOT_AVAILABLE in product.properties.get("orderStatusLink", "")
        #     not getattr(product.downloader, "order_download")
        # ):
            # first order
        logger.debug("Order product")
        product.downloader.order_download( #order_status_dict = product.downloader.order_download(
            product=product, auth=auth
        )

        if product.properties.get("orderId") is None:
            raise NotFoundError(
                "Download order failed. It can be due to a lack of product found, so you "
                f"may change 'dc_qs' argument. The one used for this order was: {dc_qs}"
            )
        # raise erreur si on a aucun asset et dire "Please check your 'dc_qs' argument: {dc_qs}"
        # return un stacitem, pas un orjson
        return ORJSONResponse(
            status_code=200,
            # headers={"Location": download_link}, # besoin de mettre un header qui correspond au contexte ?
            content={
                "description": "Product has been ordered with success. To make it available, please request the pooling endpoint by using the order:id property",
                "order:status": STATUS_STAC_MATCHING[product.properties.get("storageStatus", OFFLINE_STATUS)],
                "order:id": product.properties.get("orderId"),
            },
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
                        "application/json": {},
                    },
                }
            },
            endpoint=create_async_endpoint(self.client.order_data, DataOrderUri),
        )
        app.include_router(self.router, tags=["Collection order"])
