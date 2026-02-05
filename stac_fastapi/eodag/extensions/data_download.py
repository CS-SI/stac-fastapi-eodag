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
import mimetypes
import os
from io import BufferedReader
from pathlib import Path as FilePath
from shutil import make_archive, rmtree
from typing import Annotated, Iterator, Optional, TypedDict, Union, cast

import attr
from eodag.api.core import EODataAccessGateway
from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import ONLINE_STATUS, STAGING_STATUS, get_metadata_path_value
from eodag.utils.exceptions import EodagError
from fastapi import APIRouter, FastAPI, Path, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from stac_fastapi.api.errors import NotFoundError
from stac_fastapi.api.routes import create_async_endpoint
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest

from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.errors import (
    DownloadError,
    MisconfiguredError,
    NoMatchingCollection,
    NotAvailableError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class ZarrFileEntry(TypedDict):
    path: str
    size: int
    url: str


class BaseDataDownloadClient:
    """Defines a pattern for implementing the data download extension."""

    def _try_presign_asset(
        self,
        product: EOProduct,
        asset_name: Optional[str],
        auth: Optional[dict],
    ) -> Optional[RedirectResponse]:
        """Return a presigned URL redirect when available."""
        if product.downloader_auth and asset_name and asset_name not in ["downloadLink", "zarr"]:
            asset_values = product.assets[asset_name]
            # return presigned url if available
            try:
                presigned_url = product.downloader_auth.presign_url(asset_values)
                return RedirectResponse(presigned_url, status_code=302)
            except NotImplementedError:
                logger.info("Presigned urls not supported for %s with auth %s", product.downloader, auth)
            except EodagError:
                logger.info("Presigned url could not be fetched for %s", asset_name)
        return None

    def _handle_zarr(
        self,
        dag: EODataAccessGateway,
        product: EOProduct,
        federation_backend: str,
        collection_id: str,
        item_id: str,
        file_path: Optional[str],
    ) -> Union[StreamingResponse, RedirectResponse, JSONResponse]:
        """Handle Zarr store listing or file streaming."""
        logger.debug("Accessing Zarr store for product %s", item_id)
        try:
            # Check if zarr asset exists
            if "zarr" not in product.assets:
                logger.error(f"No zarr asset found for product {item_id}")
                logger.error(f"Available assets: {list(product.assets.keys())}")
                raise NotFoundError(
                    f"No zarr asset found for product '{item_id}'. Available assets: {list(product.assets.keys())}"
                )

            logger.debug(f"Downloading zarr store for product {item_id}")
            zarr_path = dag.download(product, extract=False, asset="zarr")
            logger.debug(f"Zarr store downloaded to: {zarr_path}")

            if not FilePath(zarr_path).exists():
                logger.error(f"Zarr store path does not exist: {zarr_path}")
                raise NotFoundError(f"Zarr store not found at {zarr_path}")

            # If file_path is provided, handle it specially
            if file_path:
                # Check if requesting the index/listing
                if file_path == "index":
                    logger.debug(f"Returning Zarr index for product {item_id}")
                    zarr_index = self._list_zarr_files(zarr_path, federation_backend, collection_id, item_id)
                    return JSONResponse(content=zarr_index)

                # Otherwise, serve the requested file
                logger.debug(f"Retrieving zarr file: {file_path}")
                file_full_path = FilePath(zarr_path) / file_path

                # Security check: ensure path doesn't escape zarr store
                try:
                    file_full_path.resolve().relative_to(FilePath(zarr_path).resolve())
                except ValueError as err:
                    logger.error(f"Path traversal attempt detected: {file_path}")
                    raise NotFoundError(f"Invalid file path: {file_path}") from err

                if not file_full_path.exists():
                    logger.error(f"File not found: {file_full_path}")
                    raise NotFoundError(f"File not found: {file_path}")

                if not file_full_path.is_file():
                    logger.error(f"Path is not a file: {file_full_path}")
                    raise NotFoundError(f"Path is not a file: {file_path}")

                # Stream the file
                filename = os.path.basename(str(file_full_path))

                # Determine content type and whether to download or display inline
                content_type, _ = mimetypes.guess_type(str(file_full_path))
                if content_type is None:
                    content_type = "application/octet-stream"

                # For text-based formats (JSON, XML, etc), display inline in browser
                # For binary formats (zarr, etc), force download
                headers = {
                    "cache-control": "public, max-age=86400",
                }

                if content_type.startswith("text/") or content_type in ["application/json", "application/xml"]:
                    # Display inline
                    headers["content-type"] = content_type
                else:
                    # Force download
                    headers["content-disposition"] = f"attachment; filename={filename}"
                    headers["content-type"] = content_type

                return StreamingResponse(
                    content=self._read_file_chunks(open(str(file_full_path), "rb")),
                    headers=headers,
                )
            try:
                if not product.downloader_auth:
                    raise NotFoundError(
                        f"Use /data/{federation_backend}/{collection_id}/{item_id}/zarr/index to list files "
                        "or access individual files directly"
                    )
                asset_values = product.assets["zarr"]
                presigned_url = product.downloader_auth.presign_url(asset_values)
                return RedirectResponse(presigned_url, status_code=302)
            except NotImplementedError as err:
                logger.info("Presigned URLs not supported for zarr asset")
                raise NotFoundError(
                    f"Use /data/{federation_backend}/{collection_id}/{item_id}/zarr/index to list files \
                    or access individual files directly"
                ) from err
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to access Zarr store: {type(e).__name__}: {e}", exc_info=True)
            raise NotFoundError(f"Failed to retrieve Zarr store for item '{item_id}': {str(e)}") from e

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

    def _read_file_chunks(self, opened_file: BufferedReader, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
        """Yield file chunks without deleting."""
        try:
            while True:
                data = opened_file.read(chunk_size)
                if not data:
                    break
                yield data
        finally:
            opened_file.close()

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

    def _list_zarr_files(
        self,
        zarr_store_path: str,
        federation_backend: str,
        collection_id: str,
        item_id: str,
    ) -> dict:
        """List all files in a Zarr store."""
        files: list[ZarrFileEntry] = []
        store_path = FilePath(zarr_store_path).resolve()

        try:
            for file_path in store_path.rglob("*"):
                if file_path.is_file():
                    # Get relative path from store root
                    rel_path = file_path.relative_to(store_path).as_posix()
                    files.append(
                        ZarrFileEntry(
                            path=rel_path,
                            size=file_path.stat().st_size,
                            url=f"/data/{federation_backend}/{collection_id}/{item_id}/zarr/{rel_path}",
                        )
                    )

            # Sort files by path
            files.sort(key=lambda x: x["path"])

            return {
                "type": "zarr-file-index",
                "item_id": item_id,
                "collection_id": collection_id,
                "backend": federation_backend,
                "store_path": str(store_path),
                "file_count": len(files),
                "files": files,
            }
        except Exception as e:
            logger.error(f"Failed to list Zarr files for {item_id}: {e}")
            raise

    def get_data_with_file(
        self,
        federation_backend: str,
        collection_id: str,
        item_id: str,
        asset_name: Optional[str],
        request: Request,
        file_path: str,
    ) -> Union[StreamingResponse, RedirectResponse, JSONResponse]:
        """Download data with file path (wrapper for get_data)."""
        return self.get_data(federation_backend, collection_id, item_id, asset_name, request, file_path)

    def get_data(
        self,
        federation_backend: str,
        collection_id: str,
        item_id: str,
        asset_name: Optional[str],
        request: Request,
        file_path: Optional[str] = None,
    ) -> Union[StreamingResponse, RedirectResponse, JSONResponse]:
        """Download an asset"""

        dag = cast(EODataAccessGateway, request.app.state.dag)  # type: ignore

        # check if the collection is known
        try:
            dag.get_collection_from_alias(collection_id)
        except NoMatchingCollection as e:
            raise NotFoundError(e) from e

        search_results = dag.search(id=item_id, collection=collection_id, provider=federation_backend)
        if len(search_results) > 0:
            product = cast(EOProduct, search_results[0])

        else:
            raise NotFoundError(
                f"Could not find {item_id} item in {collection_id} collection",
                f" for backend {federation_backend}.",
            )

        settings = get_settings()
        auto_order_whitelist = settings.auto_order_whitelist
        if federation_backend in auto_order_whitelist:
            logger.info(f"Provider {federation_backend} is whitelisted, ordering product before download")

            auth = product.downloader_auth.authenticate() if product.downloader_auth else None
            logger.debug(f"Polling product {product}")
            try:
                product.downloader.order(product=product, auth=auth)  # type: ignore
            # when a NotAvailableError is catched, it means the product is not ready and still needs to be polled
            except NotAvailableError:
                product.properties["order:status"] = STAGING_STATUS
            except Exception as e:
                if (
                    isinstance(e, DownloadError) or isinstance(e, ValidationError)
                ) and "order status could not be checked" in e.args[0]:
                    raise NotFoundError(f"Item {item_id} does not exist. Please order it first") from e
                raise NotFoundError(e) from e

        auth = product.downloader_auth.authenticate() if product.downloader_auth else None

        if product.downloader is None:
            logger.error("No downloader available for %s", product)
            raise NotFoundError(
                f"Impossible to download {item_id} item in {collection_id} collection",
                f" for backend {federation_backend}.",
            )
        if product.properties.get("order:status", ONLINE_STATUS) != ONLINE_STATUS:
            # "title" property is a fake one create by EODAG, set it to the item ID
            # (the same one as order ID) to make error message clearer
            product.properties["title"] = product.properties["id"]
            # "orderLink" property is set to auth provider conf matching url to create its auth plugin
            status_link_metadata = product.downloader.config.order_on_response["metadata_mapping"]["eodag:status_link"]
            product.properties["eodag:order_link"] = product.properties["eodag:status_link"] = get_metadata_path_value(
                status_link_metadata
            ).format(orderId=item_id)

            search_link_metadata = product.downloader.config.order_on_response["metadata_mapping"].get(
                "eodag:search_link"
            )
            if search_link_metadata:
                product.properties["eodag:search_link"] = get_metadata_path_value(search_link_metadata).format(
                    orderId=item_id
                )

            order_status_method = getattr(product.downloader, "_order_status", None)
            if not order_status_method:
                raise MisconfiguredError("Product downloader must have the order status request method")

            auth = product.downloader_auth.authenticate() if product.downloader_auth else None

            logger.debug("Poll product")
            try:
                order_status_method(product=product, auth=auth)
            # when a NotAvailableError is catched, it means the product is not ready and still needs to be polled
            except NotAvailableError:
                product.properties["order:status"] = STAGING_STATUS
            except Exception as e:
                if (
                    isinstance(e, DownloadError) or isinstance(e, ValidationError)
                ) and "order status could not be checked" in e.args[0]:
                    raise NotFoundError(f"Item {item_id} does not exist. Please order it first") from e
                raise NotFoundError(e) from e

        presigned_response = self._try_presign_asset(product, asset_name, auth)
        if presigned_response:
            return presigned_response

        # Handle zarr store - return file listing or individual file
        if asset_name == "zarr":
            return self._handle_zarr(dag, product, federation_backend, collection_id, item_id, file_path)

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
class DataDownloadUriWithFile(APIRequest):
    """Download data with file path."""

    federation_backend: Annotated[str, Path(description="Federation backend name")] = attr.ib()
    collection_id: Annotated[str, Path(description="Collection ID")] = attr.ib()
    item_id: Annotated[str, Path(description="Item ID")] = attr.ib()
    asset_name: Annotated[str, Path(description="Asset name")] = attr.ib()
    file_path: Annotated[str, Path(description="File path within zarr store")] = attr.ib()


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
        # Route for /data/{backend}/{collection}/{item}/{asset_name}
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

        # Route for /data/{backend}/{collection}/{item}/{asset_name}/{file_path}
        self.router.add_api_route(
            name="Download data with file path",
            path="/data/{federation_backend}/{collection_id}/{item_id}/{asset_name}/{file_path:path}",
            methods=["GET"],
            responses={
                200: {
                    "content": {
                        "application/octet-stream": {},
                    },
                }
            },
            endpoint=create_async_endpoint(self.client.get_data_with_file, DataDownloadUriWithFile),
        )
        app.include_router(self.router, tags=["Data download"])
