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
"""stac_fastapi.types.search module."""

from __future__ import annotations

from datetime import datetime as dt
from typing import TypeAlias

from geojson_pydantic.geometries import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from stac_fastapi.types.rfc3339 import str_to_interval
from stac_fastapi.types.search import BaseSearchPostRequest

Intersection: TypeAlias = (
    Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon | GeometryCollection
)


class EodagSearch(BaseSearchPostRequest):
    """Search model.

    Overrides the validation for datetime and spatial filter from the base request model.
    """

    @property
    def start_date(self) -> dt | None:
        """Extract the start date from the datetime string."""
        if self.datetime:
            interval = str_to_interval(self.datetime)
        else:
            return None

        if isinstance(interval, tuple):
            return interval[0]
        else:
            return interval

    @property
    def end_date(self) -> dt | None:
        """Extract the end date from the datetime string."""
        if self.datetime:
            interval = str_to_interval(self.datetime)
        else:
            return None

        if isinstance(interval, tuple) and len(interval) >= 2:
            return interval[1]
        else:
            return interval

    @property
    def spatial_filter(self) -> Intersection | None:
        """Return the WKT of the spatial filter for the search request.

        Check for both because the ``bbox`` and ``intersects`` parameters are
        mutually exclusive.
        """
        if self.bbox:
            return Polygon.from_bounds(*self.bbox)
        if self.intersects:
            return self.intersects
        return None
