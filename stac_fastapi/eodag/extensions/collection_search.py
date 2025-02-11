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
"""Collection Search extension."""

from enum import Enum
from typing import Annotated, Optional

import attr
from fastapi import FastAPI, Query
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.rfc3339 import DateTimeType, str_to_interval
from stac_fastapi.types.search import APIRequest, str2bbox
from stac_pydantic.shared import BBox


class CollectionSearchConformanceClasses(str, Enum):
    """Conformance classes for the Collection Search extension.

    See
    https://github.com/stac-api-extensions/collection-search
    """

    BASICS = "http://www.opengis.net/spec/ogcapi-common-2/1.0/conf/simple-query"
    FREETEXT_SEARCH = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#free-text"
    FILTER = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#filter"
    QUERY = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#query"
    SORT = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#sort"
    FIELDS = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#fields"


@attr.s
class CollectionSearchExtensionGetRequest(APIRequest):
    """Collection Search extension GET request model."""

    limit: Annotated[Optional[int], Query()] = attr.ib(default=None)
    bbox: Annotated[Optional[BBox], Query()] = attr.ib(default=None, converter=str2bbox)
    datetime: Annotated[Optional[DateTimeType], Query()] = attr.ib(default=None, converter=str_to_interval)
    q: Annotated[Optional[str], Query()] = attr.ib(default=None)


@attr.s
class CollectionSearchExtension(ApiExtension):
    """Collection Search extension.

    The Collection Search endpoint by default doesn't provide any query parameters
    to filter and all additional behavior will be defined in extensions.

    https://github.com/stac-api-extensions/collection-search/blob/main/README.md
    """

    GET = CollectionSearchExtensionGetRequest

    #: Conformance classes provided by the extension
    conformance_classes: list[str] = attr.ib(
        default=[
            CollectionSearchConformanceClasses.BASICS,
            CollectionSearchConformanceClasses.FREETEXT_SEARCH,
        ]
    )

    def register(self, app: FastAPI) -> None:
        """
        Register the extension with a FastAPI application.

        :param app: Target FastAPI application.
        :returns: None
        """
        pass
