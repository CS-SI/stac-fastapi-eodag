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
"""helper functions"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import unquote_plus

import orjson
from shapely.geometry import Point

if TYPE_CHECKING:
    from typing import Any, Optional, Union

    from stac_fastapi.types.rfc3339 import DateTimeType


def is_dict_str_any(var: Any) -> bool:
    """
    Verify whether the variable is of type ``dict[str, Any]``.

    :param var: The variable to check.
    :returns: ``True`` if the variable is of type ``dict[str, Any]``, ``False`` otherwise.
    """
    if isinstance(var, dict):
        return all(isinstance(k, str) for k in var.keys())  # type: ignore
    return False


def str2liststr(raw: Any) -> list[str]:
    """
    Convert ``str`` to ``list[str]``.

    :param raw: The string to convert.
    :returns: A list of strings.
    """
    if isinstance(raw, str):
        return raw.split(",")
    return raw


def str2json(k: str, v: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Decode a URL parameter and then parse it as JSON.

    :param k: The key associated with the JSON string.
    :param v: The JSON string to decode and parse.
    :returns: A dictionary if the JSON string is valid, None otherwise.
    :raises Exception: If the JSON string is invalid.
    """
    if not v:
        return None
    try:
        return orjson.loads(unquote_plus(v))
    except orjson.JSONDecodeError as e:
        raise Exception(f"{k}: Incorrect JSON object") from e


def format_datetime_range(dt_range: Union[DateTimeType, str]) -> str:
    """
    Convert a datetime object or a tuple of datetime objects to a formatted string for datetime ranges.

    :param dt_range: The date interval, which might be a single datetime or a tuple with one or two datetimes.
    :returns: A formatted string like ``YYYY-MM-DDTHH:MM:SSZ/..``, ``YYYY-MM-DDTHH:MM:SSZ``,
              or the original string input.
    """
    # Handle a single datetime object
    if isinstance(dt_range, datetime):
        return dt_range.isoformat().replace("+00:00", "Z")

    # Handle a tuple containing datetime objects or None
    elif isinstance(dt_range, tuple):
        start, end = dt_range

        # Convert start datetime to string if not None, otherwise use ".."
        start_str = start.isoformat().replace("+00:00", "Z") if start else ".."

        # Convert end datetime to string if not None, otherwise use ".."
        end_str = end.isoformat().replace("+00:00", "Z") if end else ".."

        return f"{start_str}/{end_str}"

    # Return input as-is if it's not any expected type (fallback)
    return dt_range


def dt_range_to_eodag(
    dt_range: Optional[DateTimeType] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Process a datetime input and return the start and end times in ISO 8601 format.

    :param dt_range: A single datetime, a tuple of two datetimes, or ``None``.
    :returns: A tuple containing the start and end times in ISO 8601 format,
              or ``(None, None)`` if the input is ``None``.
    """
    if isinstance(dt_range, tuple):
        start, end = dt_range
    else:
        start = end = dt_range

    start = start.isoformat().replace("+00:00", "Z") if start else None
    end = end.isoformat().replace("+00:00", "Z") if end else None

    return start, end


def check_poly_is_point(poly):
    """
    Check if the polygon is a Point and returns it if so.

    :param poly: A Shapely polygon.
    :returns: Either a `Point` or the unchanged `poly`.
    """

    if poly.area == 0 and poly.area == 0 and poly.bounds[0] == poly.bounds[2] and poly.bounds[1] == poly.bounds[3]:
        return Point(poly.exterior.coords[0])
    else:
        return poly
