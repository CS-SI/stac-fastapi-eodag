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
from itertools import product
import json
import logging
import mimetypes
import os
import re
import tempfile
from io import BufferedReader
from shutil import make_archive, rmtree
from typing import Annotated, Iterator, Optional, TypedDict, Union, cast
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile

import attr
import zarr
from eodag.api.core import EODataAccessGateway
from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import ONLINE_STATUS, STAGING_STATUS, get_metadata_path_value
from eodag.utils.exceptions import EodagError
from eodag.utils import StreamResponse
from fastapi import APIRouter, FastAPI, Path, Request
import requests
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
    """Zarr file listing item."""

    path: str
    size: int
    url: str


class StreamFileEntry(TypedDict):
    """Stream file listing item."""

    path: str
    size: Optional[int]
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
        product: EOProduct,
        base_url: str,
        federation_backend: str,
        collection_id: str,
        item_id: str,
        file_path: Optional[str],
        asset_name: Optional[str],
        auth: Optional[dict] = None,
    ) -> Union[StreamingResponse, RedirectResponse, JSONResponse]:
        """Handle Zarr store listing or file streaming."""
        # List all files in the zarr store
        try:
            stream_files = self._list_zarr_files_from_metadata(
                base_url, auth, federation_backend, collection_id, item_id, asset_name
            )
            
            return JSONResponse(
                content={
                    "type": "stream-file-index",
                    "item_id": item_id,
                    "collection_id": collection_id,
                    "backend": federation_backend,
                    "file_count": len(stream_files),
                    "files": stream_files,
                }
            )
        except Exception as e:
            logger.error(f"Failed to list zarr files: {e}")
            raise NotFoundError(f"Failed to list zarr store files: {e}") from e
       

    def _list_zarr_files_from_metadata(
        self,
        base_url: str,
        auth: Optional[dict],
        federation_backend: str,
        collection_id: str,
        item_id: str,
        asset_name: str,
    ) -> list[StreamFileEntry]:
        """List all files from zarr store by parsing .zmetadata."""
        import fsspec
        import base64
        
        files: list[StreamFileEntry] = []
        
        try:
            # Build headers for authentication if auth is provided
            headers = {}
            # if auth and isinstance(auth, dict) and "refresh_token" in auth:
            auth_str = f"anonymous:{auth.refresh_token}"
            headers["Authorization"] = "Basic " + base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            # Get mapper with fsspec
            mapper = fsspec.get_mapper(
                base_url,
                client_kwargs={
                    "headers": headers,
                    "trust_env": False
                }
            )
            
            # Read .zmetadata
            if ".zmetadata" in mapper:
                meta = json.loads(mapper[".zmetadata"])
                logger.debug(f"Found {len(meta['metadata'])} entries in .zmetadata")
                key = meta["metadata"].keys()
                # Add .zmetadata file itself to the listing to allow clients to read it and get metadata for all files in the store
                quoted_path = quote(".zmetadata", safe="/")
                files.append(
                        StreamFileEntry(
                            path=quoted_path,
                            url=f"{federation_backend}/{collection_id}/{item_id}/{asset_name}/{quoted_path}",
                        )
                    )
            else:  # try zarr v3 metadata file
                """TO DO
                .zmetadata is present for zarr v2, but not for v3, we should support both.
                For Zarr v3, there is no .zmetata but zarr.json file instead, we can try to read it and parse the metadata from it to list files in the store.
                for exemple:
                elif "zarr.json" in mapper:
                meta = json.loads(mapper["zarr.json"])
                logger.debug(f"Found {len(meta['metadata'])} entries in zarr.json")
                key = meta["metadata"].keys()
                """

                
            # Iterate through all files in the metadata
            for file_path in key:
                try:
                    quoted_path = quote(file_path, safe="/")
                    files.append(
                        StreamFileEntry(
                            path=file_path,
                            url=f"{federation_backend}/{collection_id}/{item_id}/{asset_name}/{quoted_path}",
                        )
                    )
                except Exception as e:
                    logger.debug(f"Could not get metadata for {file_path}: {e}")
            
            logger.debug(f"Listed {len(files)} zarr files")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list zarr files from metadata: {e}")
            raise

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

        zarr_asset_name = next(
                (name for name in product.assets if name.endswith(".zarr")), None
            )
        if zarr_asset_name: 
            asset_values = product.assets[zarr_asset_name]
            
            base_url = asset_values["href"]
            if file_path == "index":
                logger.debug(f"Listing zarr files for: {base_url}, auth available: {auth is not None}")
                return self._handle_zarr(product, base_url, federation_backend, collection_id, item_id, file_path, asset_name, auth)
            
            if asset_name == "zarr" and file_path != "index":
                # request data/{backend}/{collection}/{item}/zarr/{file_path} to stream a specific file in the zarr store
                base_url = base_url + "/" + file_path.lstrip("/")
                
                r = requests.get(
                    base_url, 
                    auth=auth, 
                    stream=True
                )
                data = r.json() 
                return JSONResponse(
                    content=data)
                
            if zarr_asset_name == asset_name:
                target_url = f"{base_url.rstrip('/')}/{file_path.lstrip('/')}"
                
                r = requests.get(
                    target_url, 
                    auth=auth, 
                    stream=True
                )

                return StreamingResponse(
                    r.iter_content(chunk_size=1024*1024),  
                    status_code=r.status_code,
                    media_type=r.headers.get("Content-Type", "application/octet-stream"),
                    headers={k: v for k, v in r.headers.items() if k.lower() not in ["content-encoding", "transfer-encoding"]}
                )
            
        presigned_response = self._try_presign_asset(product, asset_name, auth)
        if presigned_response:
            return presigned_response
        
        # stream_asset = asset_name if asset_name != "downloadLink" else None
        # stream_asset_with_path = (
        #     rf"{re.escape(asset_name)}/{re.escape(file_path)}"
        #     if asset_name and file_path and file_path != "index" and asset_name != "downloadLink"
        #     else None
        # )

        try:
            s = product.downloader._stream_download_dict(
                product,
                auth=auth,
                asset=asset_name if asset_name != "downloadLink" else None, 
                wait=-1,
                timeout=-1,
            )
            # asset=stream_asset_with_path or stream_asset,
            # if file_path == "index":
            #     return self._handle_zarr(product, s, federation_backend, collection_id, item_id, file_path, asset_name)
            download_stream = StreamingResponse(
                content=s.content,
                headers=s.headers,
                media_type=s.media_type,
                status_code=s.status_code or 200,
            )
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
