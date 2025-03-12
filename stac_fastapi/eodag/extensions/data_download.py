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
"""Data-download extension."""

import glob
import logging
import os
from io import BufferedReader
from shutil import make_archive, rmtree
from typing import Annotated, Iterator, Optional, cast

import attr
from eodag.api.core import EODataAccessGateway
from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import ONLINE_STATUS, STAGING_STATUS
from fastapi import APIRouter, FastAPI, Path, Request
from fastapi.responses import StreamingResponse
from stac_fastapi.api.errors import NotFoundError
from stac_fastapi.api.routes import create_async_endpoint
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest

from stac_fastapi.eodag.errors import (
    DownloadError,
    MisconfiguredError,
    NoMatchingProductType,
    NotAvailableError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class BaseDataDownloadClient:
    """Defines a pattern for implementing the data download extension."""

    def _file_to_stream(
        self,
        file_path: str,
    ) -> StreamingResponse:
        """Break a file into chunck and return it as a byte stream"""
        if os.path.isdir(file_path):
            # do not zip if dir contains only one file
            all_filenames = [
                f for f in glob.glob(os.path.join(file_path, "**", "*"), recursive=True) if os.path.isfile(f)
            ]
            if len(all_filenames) == 1:
                filepath_to_stream = all_filenames[0]
            else:
                filepath_to_stream = f"{file_path}.zip"
                logger.debug(
                    "Building archive for downloaded product path %s",
                    filepath_to_stream,
                )
                make_archive(file_path, "zip", file_path)
                rmtree(file_path)
        else:
            filepath_to_stream = file_path

        filename = os.path.basename(filepath_to_stream)
        return StreamingResponse(
            content=self._read_file_chunks_and_delete(open(filepath_to_stream, "rb")),
            headers={
                "content-disposition": f"attachment; filename={filename}",
            },
        )

    def _read_file_chunks_and_delete(self, opened_file: BufferedReader, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
        """Yield file chunks and delete file when finished."""
        while True:
            data = opened_file.read(chunk_size)
            if not data:
                opened_file.close()
                os.remove(opened_file.name)
                logger.debug("%s deleted after streaming complete", opened_file.name)
                break
            yield data
        yield data

    def get_data(
        self,
        federation_backend: str,
        collection_id: str,
        item_id: str,
        asset_name: Optional[str],
        request: Request,
    ) -> StreamingResponse:
        """Download an asset"""

        dag = cast(EODataAccessGateway, request.app.state.dag)  # type: ignore

        # check if the collection is known
        try:
            product_type = dag.get_product_type_from_alias(collection_id)
        except NoMatchingProductType as e:
            raise NotFoundError(e) from e

        search_results = dag.search(id=item_id, productType=product_type, provider=federation_backend)
        if len(search_results) > 0:
            product = cast(EOProduct, search_results[0])

        else:
            raise NotFoundError(
                f"Could not find {item_id} item in {product_type} collection",
                f" for backend {federation_backend}.",
            )
        auth = product.downloader_auth.authenticate() if product.downloader_auth else None

        if product.downloader is None:
            logger.error("No downloader available for %s", product)
            raise NotFoundError(
                f"Impossible to download {item_id} item in {collection_id} collection",
                f" for backend {federation_backend}.",
            )
        if product.properties["storageStatus"] != ONLINE_STATUS:
            # "title" property is a fake one create by EODAG, set it to the item ID
            # (the same one as order ID) to make error message clearer
            product.properties["title"] = product.properties["id"]
            # "orderLink" property is set to auth provider conf matching url to create its auth plugin
            product.properties["orderLink"] = product.properties["orderStatusLink"] = (
                product.downloader.config.order_on_response["metadata_mapping"]["orderStatusLink"].format(
                    orderId=item_id
                )
            )

            if product.downloader.config.order_on_response["metadata_mapping"].get("searchLink"):
                product.properties["searchLink"] = product.downloader.config.order_on_response["metadata_mapping"][
                    "searchLink"
                ].format(orderId=item_id)

            if not getattr(product.downloader, "_order_status", None):
                raise MisconfiguredError("Product downloader must have the order status request method")

            auth = product.downloader_auth.authenticate() if product.downloader_auth else None

            logger.debug("Poll product")
            try:
                _ = product.downloader._order_status(product=product, auth=auth)
            # when a NotAvailableError is catched, it means the product is not ready and still needs to be polled
            except NotAvailableError:
                product.properties["storageStatus"] = STAGING_STATUS
            except Exception as e:
                if (
                    isinstance(e, DownloadError) or isinstance(e, ValidationError)
                ) and "order status could not be checked" in e.args[0]:
                    raise NotFoundError(f"Item {item_id} does not exist. Please order it first") from e
                raise NotFoundError(e) from e

        try:
            s = product.downloader._stream_download_dict(
                product,
                auth=auth,
                asset=asset_name if asset_name != "downloadLink" else None,
                wait=-1,
                timeout=-1,
            )
            download_stream = StreamingResponse(s.content, headers=s.headers, media_type=s.media_type)
        except NotImplementedError:
            logger.warning(
                "Download streaming not supported for %s: downloading locally then delete",
                product.downloader,
            )
            download_stream = self._file_to_stream(dag.download(product, extract=False, asset=asset_name))

        return download_stream


@attr.s
class DataDownloadUri(APIRequest):
    """Download data."""

    federation_backend: Annotated[str, Path(description="Federation backend name")] = attr.ib()
    collection_id: Annotated[str, Path(description="Collection ID")] = attr.ib()
    item_id: Annotated[str, Path(description="Item ID")] = attr.ib()
    asset_name: Annotated[str, Path(description="Item ID")] = attr.ib()


@attr.s
class DataDownload(ApiExtension):
    """Data-download Extension.

    The download-data extension allow to download data directly through the EODAG STAC
    server.

    Usage:
    ------

        ``GET /data/{federation_backend}/{collection_id}/{item_id}/{asset_id}``
    """

    client: BaseDataDownloadClient = attr.ib(factory=BaseDataDownloadClient)
    router: APIRouter = attr.ib(factory=APIRouter)

    def register(self, app: FastAPI) -> None:
        """
        Register the extension with a FastAPI application.

        :param app: Target FastAPI application.
        :returns: None
        """
        self.router.prefix = app.state.router_prefix
        self.router.add_api_route(
            name="Download data",
            path="/data/{federation_backend}/{collection_id}/{item_id}/{asset_name}",
            methods=["GET"],
            responses={
                200: {
                    "content": {
                        "application/octet-stream": {},
                    },
                }
            },
            endpoint=create_async_endpoint(self.client.get_data, DataDownloadUri),
        )
        app.include_router(self.router, tags=["Data download"])
