# -*- coding: utf-8 -*-
# Copyright 2024, CS GROUP - France, https://www.cs-soprasteria.com
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
"""FastAPI application using EODAG."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import stac_fastapi.api.errors
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import ORJSONResponse
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import (
    EmptyRequest,
    ItemCollectionUri,
    create_get_request_model,
    create_post_request_model,
    create_request_model,
)
from stac_fastapi.extensions.core import FilterExtension, QueryExtension, SortExtension

from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.core import EodagCoreClient
from stac_fastapi.eodag.dag import init_dag
from stac_fastapi.eodag.errors import add_exception_handlers, exception_handler_factory
from stac_fastapi.eodag.extensions.collection_order import (
    BaseCollectionOrderClient,
    CollectionOrderExtension,
)
from stac_fastapi.eodag.extensions.collection_search import CollectionSearchExtension
from stac_fastapi.eodag.extensions.data_download import DataDownload
from stac_fastapi.eodag.extensions.ecmwf import EcmwfExtension
from stac_fastapi.eodag.extensions.filter import FiltersClient
from stac_fastapi.eodag.extensions.pagination import PaginationExtension
from stac_fastapi.eodag.extensions.stac import (
    ElectroOpticalExtension,
    FederationExtension,
    OrderExtension,
    ProcessingExtension,
    ProductExtension,
    SarExtension,
    SatelliteExtension,
    ScientificCitationExtension,
    StorageExtension,
    TimestampExtension,
    ViewGeometryExtension,
)
from stac_fastapi.eodag.logs import RequestIDMiddleware, init_logging
from stac_fastapi.eodag.models.stac_metadata import create_stac_metadata_model

if TYPE_CHECKING:
    from typing import AsyncGenerator

init_logging()

settings = get_settings()

stac_metadata_model = create_stac_metadata_model(
    extensions=[
        SarExtension(),
        SatelliteExtension(),
        TimestampExtension(),
        ProcessingExtension(),
        ViewGeometryExtension(),
        ElectroOpticalExtension(),
        FederationExtension(),
        ScientificCitationExtension(),
        ProductExtension(),
        StorageExtension(),
        OrderExtension(),
        EcmwfExtension(),
    ]
)
extensions_map = {
    "collection-search": CollectionSearchExtension(),
    "pagination": PaginationExtension(),
    "filter": FilterExtension(client=FiltersClient(stac_metadata_model=stac_metadata_model)),
    "query": QueryExtension(),
    "sort": SortExtension(),
    "collection-order": CollectionOrderExtension(
        client=BaseCollectionOrderClient(stac_metadata_model=stac_metadata_model)
    ),
    "data-download": DataDownload(),
}

if enabled_extensions := os.getenv("ENABLED_EXTENSIONS"):
    extensions = [extensions_map[extension_name] for extension_name in enabled_extensions.split(",")]
else:
    extensions = list(extensions_map.values())

for e in extensions:
    if isinstance(e, CollectionOrderExtension):
        e.client.extensions = extensions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """API init and tear-down"""
    init_dag(app)
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""):
        from stac_fastapi.eodag.telemetry import instrument_eodag

        instrument_eodag(app.state.dag)
    # init_cache(app)
    app.state.stac_metadata_model = stac_metadata_model
    yield


app = FastAPI(
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=None,
    lifespan=lifespan,
)

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""):
    from stac_fastapi.eodag.telemetry import instrument_fastapi

    instrument_fastapi(app)

add_exception_handlers(app)
app.add_middleware(RequestIDMiddleware)


search_post_model = create_post_request_model(extensions)
search_get_model = create_get_request_model(extensions)


collections_model = create_request_model(
    "CollectionsRequest",
    base_model=EmptyRequest,
    extensions=[e for e in extensions if isinstance(e, CollectionSearchExtension)],
    request_type="GET",
)

item_collection_model = create_request_model(
    "ItemsRequest",
    base_model=ItemCollectionUri,
    extensions=[e for e in extensions if isinstance(e, PaginationExtension)],
    request_type="GET",
)


client = EodagCoreClient(post_request_model=search_post_model, stac_metadata_model=stac_metadata_model)

stac_fastapi.api.errors.exception_handler_factory = exception_handler_factory

api = StacApi(
    app=app,
    settings=settings,
    extensions=extensions,
    client=client,
    response_class=ORJSONResponse,
    search_get_request_model=search_get_model,
    search_post_request_model=search_post_model,
    collections_get_request_model=collections_model,
    items_get_request_model=item_collection_model,
)


def run():
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        uvicorn.run(
            "stac_fastapi.eodag.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload,
            root_path=os.getenv("UVICORN_ROOT_PATH", ""),
        )
    except ImportError as e:
        raise RuntimeError("Uvicorn must be installed in order to use command") from e


if __name__ == "__main__":
    run()
