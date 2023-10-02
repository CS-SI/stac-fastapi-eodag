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
# limitations under the License.
"""FastAPI application using EODAG.

Enables the extensions specified as a comma-delimited list in
the ENABLED_EXTENSIONS environment variable (e.g. `query`).
If the variable is not set, enables all extensions.
"""

import os
import logging
import traceback
from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.extensions.core import ContextExtension

from starlette.exceptions import HTTPException as StarletteHTTPException

from stac_fastapi.eodag.config import Settings
from stac_fastapi.eodag.core import EodagCoreClient
from stac_fastapi.eodag.eodag_types.search import EodagSearch
from stac_fastapi.eodag.extensions.pagination import PaginationExtension

from eodag.utils.exceptions import (
    AuthenticationError,
    DownloadError,
    MisconfiguredError,
    NoMatchingProductType,
    NotAvailableError,
    RequestError,
    UnsupportedProductType,
    UnsupportedProvider,
    ValidationError,
)

# TODO: can we improve logging handling integration with EODAG ?
# from eodag.utils.logging import setup_logging

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_format = (
    "%(asctime)-15s %(name)s %(levelname)s (%(module)s tid=%(thread)d) %(message)s"
)
logging.basicConfig(level=log_level, format=log_format)
# logging.basicConfig(level=log_level)
# log_level_map = {logging.NOTSET: 0, logging.DEBUG: 3}
# setup_logging(log_level_map.get(log_level, 2), no_progress_bar=True)


logger = logging.getLogger(__name__)

settings = Settings()
extensions_map = {
    "context": ContextExtension(),
    "pagination": PaginationExtension(),
}

if enabled_extensions := os.getenv("ENABLED_EXTENSIONS"):
    extensions = [
        extensions_map[extension_name]
        for extension_name in enabled_extensions.split(",")
    ]
else:
    extensions = list(extensions_map.values())

post_request_model = create_post_request_model(extensions, base_model=EodagSearch)

async def log_request_body(request: Request):
    body = await request.json()
    logger.debug(f"Request body: {body}")
    return

api = EodagStacApi(
    settings=settings,
    client=EodagCoreClient(post_request_model=post_request_model),
    extensions=extensions,
    title="eodag-stac-fastapi",
    api_version="0.1",
    description="eodag-stac-fastapi",
    response_class=ORJSONResponse,
    search_get_request_model=create_get_request_model(extensions),
    search_post_request_model=post_request_model,
    pagination_extension=PaginationExtension,
    route_dependencies=[
        ([{"path": "/search", "method": "POST"}], [Depends(log_request_body)])
    ],
)

app = api.app


@app.middleware("http")
async def log_request(request: Request, call_next):
    logging.info(f"{request.method} {request.url.path}")
    logger.debug(f"Request query parameters: {dict(request.query_params)}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    response = await call_next(request)
    return response


@app.exception_handler(DownloadError)
@app.exception_handler(RequestError)
@app.exception_handler(MisconfiguredError)
@app.exception_handler(AuthenticationError)
@app.exception_handler(StarletteHTTPException)
async def default_exception_handler(request: Request, error):
    """Default errors handle"""
    description = (
        getattr(error, "description", None)
        or getattr(error, "detail", None)
        or "An error occured"
    )

    status_code = getattr(error, "status_code", 500)
    if status_code == 500:
        logger.error(f"{type(error).__name__}: {error}")

    return ORJSONResponse(
        status_code=status_code,
        content={"description": description},
    )


@app.exception_handler(NoMatchingProductType)
@app.exception_handler(UnsupportedProductType)
@app.exception_handler(UnsupportedProvider)
@app.exception_handler(ValidationError)
async def handle_invalid_usage(request: Request, error):
    """Invalid usage [400] errors handle"""
    logger.warning(traceback.format_exc())
    error.status_code = 400
    return await default_exception_handler(request, error)


@app.exception_handler(NotAvailableError)
async def handle_resource_not_found(request: Request, error):
    """Not found [404] errors handle"""
    error.status_code = 404
    return await default_exception_handler(request, error)


def run():
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        uvicorn.run(
            "stac_fastapi.eodag.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_config=None,
            reload=settings.reload,
            root_path=os.getenv("UVICORN_ROOT_PATH", ""),
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    run()
