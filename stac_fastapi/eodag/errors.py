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
"""Errors helper"""

import logging
from typing import NotRequired, Tuple, Type, TypedDict

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from starlette import status

from eodag.rest.types.eodag_search import EODAGSearch
from eodag.utils.exceptions import (
    AuthenticationError,
    DownloadError,
    EodagError,
    MisconfiguredError,
    NoMatchingProductType,
    NotAvailableError,
    RequestError,
    TimeOutError,
    UnsupportedProductType,
    UnsupportedProvider,
    ValidationError,
)

EODAG_DEFAULT_STATUS_CODES: dict[type, int] = {
    AuthenticationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DownloadError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    MisconfiguredError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    NotAvailableError: status.HTTP_404_NOT_FOUND,
    NoMatchingProductType: status.HTTP_404_NOT_FOUND,
    TimeOutError: status.HTTP_504_GATEWAY_TIMEOUT,
    UnsupportedProductType: status.HTTP_404_NOT_FOUND,
    UnsupportedProvider: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_400_BAD_REQUEST,
}

logger = logging.getLogger("eodag.rest.server")


class SearchError(TypedDict):
    """Represents a EODAG Error"""

    provider: str
    error: str
    status_code: int
    message: NotRequired[str]
    detail: NotRequired[str]


class ResponseSearchError(Exception):
    """Represent a EODAG search error response"""

    _alias_to_field_cache: dict[str, str] = {}

    def __init__(
        self, errors: list[Tuple[str, Exception]], stac_metadata_model: Type[BaseModel]
    ) -> None:
        """Initialize error response class."""
        self._errors = errors
        self._stac_medatata_model = stac_metadata_model

    def _eodag_to_stac(self, value: str) -> str:
        """Convert EODAG name to STAC."""
        if not self._alias_to_field_cache:
            self._alias_to_field_cache = {
                field.alias or str(field.validation_alias): name
                for name, field in self._stac_medatata_model.model_fields.items()
            }
        return self._alias_to_field_cache.get(value, value)

    @property
    def errors(self):
        """Return errors."""
        errors: list[SearchError] = []
        for name, exc in self._errors:
            error: SearchError = {
                "provider": name,
                "error": exc.__class__.__name__,
                "status_code": EODAG_DEFAULT_STATUS_CODES.get(
                    type(exc), getattr(exc, "status_code", None)
                )
                or 500,
            }

            if exc.args:
                error["message"] = exc.args[0]

            if len(exc.args) > 1:
                error["detail"] = " ".join(exc.args[1:])

            if type(exc) in (MisconfiguredError, AuthenticationError):
                logger.error("%s: %s", type(exc).__name__, str(exc))
                error["message"] = (
                    "Internal server error: please contact the administrator"
                )
                error.pop("detail", None)

            if params := getattr(exc, "parameters", None):
                for error_param in params:
                    stac_param = self._eodag_to_stac(error_param)
                    exc.message = exc.message.replace(error_param, stac_param)
                error["message"] = exc.message

            errors.append(error)

        return errors

    @property
    def status_code(self) -> int:
        """Get global errors status code."""
        if len(self._errors) == 1:
            return self.errors[0]["status_code"]

        return 400


async def response_search_error_handler(
    request: Request, exc: ResponseSearchError
) -> ORJSONResponse:
    """Handle ResponseSearchError exceptions"""
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"errors": exc.errors},
    )


async def eodag_errors_handler(request: Request, exc: EodagError) -> ORJSONResponse:
    """Handler for EODAG errors"""
    code = EODAG_DEFAULT_STATUS_CODES.get(type(exc), getattr(exc, "status_code", 500))
    detail = f"{type(exc).__name__}: {str(exc)}"

    if type(exc) in (MisconfiguredError, AuthenticationError, TimeOutError):
        logger.error("%s: %s", type(exc).__name__, str(exc))

    if type(exc) in (MisconfiguredError, AuthenticationError):
        detail = "Internal server error: please contact the administrator"

    if params := getattr(exc, "parameters", None):
        for error_param in params:
            stac_param = EODAGSearch.to_stac(error_param)
            exc.message = exc.message.replace(error_param, stac_param)
        detail = exc.message

    return ORJSONResponse(
        status_code=code,
        content={"description": detail},
    )


def add_exception_handlers(
    app: FastAPI
) -> None:
    """Add exception handlers to the FastAPI application.

    Args:
        app: the FastAPI application.

    Returns:
        None
    """
    app.add_exception_handler(RequestError, eodag_errors_handler)
    for exc in EODAG_DEFAULT_STATUS_CODES:
        app.add_exception_handler(exc, eodag_errors_handler)

    app.add_exception_handler(ResponseSearchError, response_search_error_handler)
