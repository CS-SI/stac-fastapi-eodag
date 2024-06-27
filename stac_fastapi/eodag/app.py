"""FastAPI application using EODAG."""

# -*- coding: utf-8 -*-
# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
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
import logging
import os
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import ORJSONResponse
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model

# from stac_fastapi.eodag.api import EodagStacApi
from stac_fastapi.eodag.config import Settings
from stac_fastapi.eodag.core import EodagCoreClient
from stac_fastapi.eodag.dag import init_dag
from stac_fastapi.eodag.eodag_types.search import EodagSearch

logging.basicConfig(
    format="%(asctime)-15s %(name)-32s [%(levelname)-8s] (tid=%(thread)d) %(message)s"
)

logger = logging.getLogger(__name__)


async def log_request_body(request: Request):
    """log request body"""
    logger.warning("Hello HERE!!!")
    # body = await request.json()
    # logger.debug(f"Request body: {body}")
    return


# @app.middleware("http")
# async def log_request(request: Request, call_next):
#     """log requ"""
#     logging.info(f"{request.method} {request.url.path}")
#     logger.debug(f"Request query parameters: {dict(request.query_params)}")
#     logger.debug(f"Request headers: {dict(request.headers)}")
#     response = await call_next(request)
#     return response

settings = Settings.from_environment()

extensions = []


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """API init and tear-down"""
    init_dag(app)
    # init_cache(app)
    yield


app = FastAPI(
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=None,
    lifespan=lifespan,
)


post_request_model = create_post_request_model(extensions, base_model=EodagSearch)
get_request_model = create_get_request_model(extensions)
api = StacApi(
    app=app,
    settings=settings,
    extensions=extensions,
    client=EodagCoreClient(post_request_model=post_request_model),
    response_class=ORJSONResponse,
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
    route_dependencies=[
        ([{"path": "*", "method": "GET"}], [Depends(log_request_body)]),
        ([{"path": "/search", "method": "POST"}], [Depends(log_request_body)]),
    ],
)


def run():
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        logging_config = uvicorn.config.LOGGING_CONFIG
        if settings.debug:
            logging_config["loggers"]["uvicorn"]["level"] = "DEBUG"
            logging_config["loggers"]["uvicorn.error"]["level"] = "DEBUG"
            logging_config["loggers"]["uvicorn.access"]["level"] = "DEBUG"
        logging_config["formatters"]["default"]["fmt"] = (
            "%(asctime)-15s %(name)-32s [%(levelname)-8s] (tid=%(thread)d) %(message)s"
        )
        logging_config["formatters"]["access"]["fmt"] = (
            "%(asctime)-15s %(name)-32s [%(levelname)-8s] %(message)s"
        )
        logging_config["loggers"]["eodag"] = {
            "handlers": ["default"],
            "level": "DEBUG" if settings.debug else "INFO",
            "propagate": False,
        }

        uvicorn.run(
            "stac_fastapi.eodag.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_config=logging_config,
            reload=settings.reload,
            root_path=os.getenv("UVICORN_ROOT_PATH", ""),
        )
    except ImportError as e:
        raise RuntimeError("Uvicorn must be installed in order to use command") from e


if __name__ == "__main__":
    run()
