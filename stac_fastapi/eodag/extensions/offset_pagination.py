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
"""Offset pagination extension."""

from typing import Annotated
import attr
from fastapi import Query
from pydantic import NonNegativeInt
from stac_fastapi.extensions.core.pagination import OffsetPaginationExtension as BaseOffsetPaginationExtension
from stac_fastapi.types.search import APIRequest

@attr.s
class GETOffsetPagination(APIRequest):
    """Offset pagination for GET requests."""

    offset: Annotated[NonNegativeInt, Query()] = attr.ib(default=0)


@attr.s
class OffsetPaginationExtension(BaseOffsetPaginationExtension):
    """Customized Offset Pagination.

    This extension overrides the default GET pagination class to apply a modified
    offset parameter definition. Specifically, we enforce a non-negative integer
    constraint and potentially adjust default values.

    A new GET class (`GETOffsetPagination`) is defined to include these changes,
    so they are correctly reflected in both the request validation and the
    generated OpenAPI schema.
    """

    GET = GETOffsetPagination
