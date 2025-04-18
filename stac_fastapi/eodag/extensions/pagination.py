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
"""Pagination extension. Override to default page to 1."""

from dataclasses import dataclass
from typing import Annotated

import attr
from fastapi import Query
from pydantic import BaseModel
from stac_fastapi.extensions.core import PaginationExtension as BasePaginationExtension
from stac_fastapi.types.search import APIRequest


class POSTPagination(BaseModel):
    """Page based pagination for POST requests."""

    page: int = 1


@attr.s
class GETPagination(APIRequest):
    """Page based pagination for GET requests."""

    page: Annotated[int, Query(description="Returns results of this page")] = attr.ib(default=1)


@attr.s
class PaginationExtension(BasePaginationExtension):
    """
    Override pagination to define page attribute as an integer instead of a string
    """

    GET = GETPagination
    POST = POSTPagination
