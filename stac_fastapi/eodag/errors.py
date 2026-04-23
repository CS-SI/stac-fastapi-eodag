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
"""Errors helper"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, TypedDict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, ORJSONResponse
from pydantic import ValidationError as pydanticValidationError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from eodag.utils.exceptions import (
    AuthenticationError,
    DownloadError,
    MisconfiguredError,
    NoMatchingCollection,
    NotAvailableError,
    RequestError,
    TimeOutError,
    UnsupportedCollection,
    UnsupportedProvider,
    ValidationError,
)
from stac_fastapi.eodag.logs import request_id_context

if TYPE_CHECKING:
    from fastapi import FastAPI, Request
    from pydantic import BaseModel
    from typing_extensions import NotRequired


EODAG_DEFAULT_STATUS_CODES: dict[type, int] = {
    AuthenticationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DownloadError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    MisconfiguredError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    NotAvailableError: status.HTTP_404_NOT_FOUND,
    NoMatchingCollection: status.HTTP_404_NOT_FOUND,
    TimeOutError: status.HTTP_504_GATEWAY_TIMEOUT,
    UnsupportedCollection: status.HTTP_404_NOT_FOUND,
    UnsupportedProvider: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    RequestError: status.HTTP_400_BAD_REQUEST,
}

logger = logging.getLogger(__name__)


def exception_handler_factory(status_code: int):
    """Overide exception_handler_factory to include tickets"""

    def handler(request: Request, exc: Exception):
        """I handle exceptions"""
        return JSONResponse(
            content={"code": status_code, "ticket": request_id_context.get(), "description": str(exc)},
            status_code=status_code,
        )

    return handler


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

    errors: list[SearchError]

    def __init__(self, errors: list[tuple[str, Exception]], stac_metadata_model: type[BaseModel]) -> None:
        """Initialize error response class."""
        self._errors = errors
        self._stac_medatata_model = stac_metadata_model

        self.errors = []
        for name, exc in self._errors:
            error: SearchError = {
                "provider": name,
                "error": exc.__class__.__name__,
                "status_code": EODAG_DEFAULT_STATUS_CODES.get(type(exc), getattr(exc, "status_code", 500)),
            }

            if exc.args:
                error["message"] = exc.args[0]

            if len(exc.args) > 1:
                error["detail"] = " ".join([str(i) for i in exc.args[1:]])

            if type(exc) in (MisconfiguredError, AuthenticationError):
                logger.error("%s: %s", type(exc).__name__, str(exc))
                error["message"] = "Internal server error: please contact the administrator"
                error.pop("detail", None)

            if params := getattr(exc, "parameters", None):
                error["message"] = getattr(exc, "message", "")
                for error_param in params:
                    stac_param = self._eodag_to_stac(error_param)
                    error["message"] = error["message"].replace(error_param, stac_param)

            self.errors.append(error)

    def _eodag_to_stac(self, value: str) -> str:
        """Convert EODAG name to STAC."""
        if not self._alias_to_field_cache:
            self._alias_to_field_cache = {
                field.alias or str(field.validation_alias): name
                for name, field in self._stac_medatata_model.model_fields.items()
            }
        return self._alias_to_field_cache.get(value, value)

    @property
    def status_code(self) -> int:
        """Get global errors status code."""
        if len(self.errors) == 1:
            return self.errors[0]["status_code"]

        return 400


async def eodag_errors_handler(request: Request, exc: Exception) -> ORJSONResponse:
    """Handler for EODAG errors"""
    code = EODAG_DEFAULT_STATUS_CODES.get(type(exc), getattr(exc, "status_code", 500)) or 500
    detail = f"{type(exc).__name__}: {str(exc)}"

    if type(exc) in (MisconfiguredError, AuthenticationError, TimeOutError):
        logger.error("%s: %s", type(exc).__name__, str(exc))

    if type(exc) in (MisconfiguredError, AuthenticationError):
        detail = "Internal server error: please contact the administrator"

    if params := getattr(exc, "parameters", None):
        detail = getattr(exc, "message", "")
        for error_param in params:
            stac_param = request.app.state.stac_metadata_model.to_stac(error_param)
            detail = detail.replace(error_param, stac_param)

    return ORJSONResponse(
        status_code=code,
        content={"code": str(code), "ticket": request_id_context.get(), "description": detail},
    )


def error_handler(request: Request, error: Exception) -> ORJSONResponse:
    """Handle errors"""
    code = getattr(error, "status_code", 400)
    description = (
        getattr(error, "description", None) or getattr(error, "detail", None) or str(error) or f" ({str(error)})"
    )
    errors = getattr(error, "errors", [])
    if not isinstance(errors, Iterable):
        errors = [errors]
    if errors != []:
        description = "Something went wrong"
        code = min(error.get("status_code", 500) for error in errors)
        return ORJSONResponse(
            status_code=code,
            content={
                "code": str(code),
                "ticket": request_id_context.get(),
                "description": description,
                "errors": errors,
            },
        )

    return ORJSONResponse(
        status_code=code,
        content={"code": str(code), "ticket": request_id_context.get(), "description": description},
    )


def pydantic_validation_handler(request: Request, error: Exception) -> ORJSONResponse:
    """Special handling for pydantic errors. They are a subtype of built-in ValueError."""

    if not isinstance(error, pydanticValidationError):
        raise Exception("Invalid handler used.")

    error_header = f"{error.error_count()} error(s). "
    error_messages = [
        f"{err['loc'][0] if len(err['loc']) == 1 else list(err['loc'])}: {err['msg']}" if err["loc"] else err["msg"]
        for err in error.errors()
    ]
    formated_error = error_header + "; ".join(set(error_messages))

    return error_handler(request, ValueError(formated_error))


def add_exception_handlers(app: FastAPI) -> None:
    """
    Add exception handlers to the FastAPI application.

    :param app: The FastAPI application.
    :returns: None
    """
    app.add_exception_handler(StarletteHTTPException, error_handler)
    app.add_exception_handler(AssertionError, error_handler)
    app.add_exception_handler(pydanticValidationError, pydantic_validation_handler)
    app.add_exception_handler(ValueError, error_handler)
    for exc in EODAG_DEFAULT_STATUS_CODES:
        app.add_exception_handler(exc, eodag_errors_handler)
    app.add_exception_handler(ResponseSearchError, error_handler)
