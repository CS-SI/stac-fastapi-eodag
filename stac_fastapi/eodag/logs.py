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
"""Custom logging formatter for Uvicorn access logs."""

import logging
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Tuple, cast

from starlette.middleware.base import BaseHTTPMiddleware

from eodag import setup_logging
from stac_fastapi.eodag.config import get_settings

request_id_context: ContextVar[str] = ContextVar("request_id", default="None")


# Prevent successful health check pings from being logged
class LivenessFilter(logging.Filter):
    """Filter out requests to the liveness probe endpoint"""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter method"""
        if not record.args or len(record.args) != 5:
            return True

        args = cast(Tuple[str, str, str, str, int], record.args)
        endpoint = args[2]
        status = args[4]
        if endpoint == "/_mgmt/ping" and status == 200:
            return False

        return True


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add a unique request ID for each incoming request."""

    async def dispatch(self, request, call_next):
        """Add ID to each request"""
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = str(request_id)
        request_id_context.set(request_id)

        response = await call_next(request)

        return response


class CustomFormatter(logging.Formatter):
    """custom logging formatter"""

    def alias_logger_name(self, name: str) -> str:
        """Replace logger name prefix with alias 'stac_eodag' if it starts with 'stac_fastapi.eodag'."""
        prefix = "stac_fastapi.eodag"
        alias = "stac_eodag"
        if name.startswith(prefix):
            name = alias + name[len(prefix) :]

        name = name.replace(".extensions.", ".ext.")
        return name

    def format(self, record):
        """Add a unique log ID and
        custom timestamp in the log output."""
        request_id = request_id_context.get()
        if request_id == "None":
            request_id = ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger_name = self.alias_logger_name(record.name)
        log_message = super().format(record)

        log_message = f"{timestamp} {logger_name:<32} [{record.levelname:<8}] [{request_id:<8}] {log_message}"

        return log_message


def init_logging():
    """Initialize the logging configuration"""
    settings = get_settings()

    log_level = logging.DEBUG if settings.debug else logging.INFO

    setup_logging(3 if settings.debug else 2, no_progress_bar=True)

    custom_formatter = CustomFormatter()

    logging.basicConfig(level=log_level)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(custom_formatter)

    for logger_name in ("eodag", "uvicorn", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(custom_formatter)

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.addFilter(LivenessFilter())
