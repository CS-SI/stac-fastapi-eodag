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
"""Request validation extension."""

from typing import Annotated, List, Optional

import attr
from fastapi import FastAPI, Query
from pydantic import (
    BaseModel,
    Field,
)
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest


class POSTValidate(BaseModel):
    """Validate for POST requests."""

    # Cannot use `validate` to avoid shadowing attribute in parent class `BaseModel`
    validate_request: Optional[bool] = Field(None, description="Validate the request")  # noqa: E501


@attr.s
class GETValidate(APIRequest):
    """Validate for GET requests."""

    validate_request: Annotated[Optional[bool], Query(description="Validate the request")] = attr.ib(default=None)


@attr.s
class ValidateExtension(ApiExtension):
    """Validate request extension."""

    GET = GETValidate
    POST = POSTValidate

    conformance_classes: List[str] = attr.ib(factory=list)
    schema_href: Optional[str] = attr.ib(default=None)

    def register(self, app: FastAPI) -> None:
        """Register the extension with a FastAPI application.

        Args:
            app: target FastAPI application.

        Returns:
            None
        """
        pass
