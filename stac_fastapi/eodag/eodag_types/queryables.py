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
"""stac_fastapi.types.queryables module."""

from typing import Any, Optional, Union

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from stac_fastapi.types.rfc3339 import parse_single_date, str_to_interval


class QueryablesGetParams(BaseModel):
    """Store GET Queryables query params"""

    collection: Optional[str] = Field(default=None)
    provider: Optional[str] = Field(default=None)
    start_datetime: Union[list[str], str, None] = Field(default=None)
    end_datetime: Union[list[str], str, None] = Field(default=None)
    datetime: Union[list[str], str, None] = Field(default=None)

    model_config = ConfigDict(extra="allow")

    @field_validator("start_datetime", "end_datetime")
    @classmethod
    def validate_start_end_datetime(cls, values: Optional[list[str]]) -> Optional[str]:
        """
        datetimes must be valid RFC3339 strings
        we assume that only one start_datetime/end_datetime filter is used
        """
        if not values:
            raise ValueError
        try:
            parse_single_date(values[0])
            return values[0]
        except ValueError:
            raise

    @field_validator("datetime")
    @classmethod
    def validate_datetime(cls, values: Optional[list[str]]) -> Optional[str]:
        """
        datetimes must be either single datetime or range separated by "/",
        we assume that only one datetime filter is used
        """
        if not values:
            raise ValueError
        try:
            str_to_interval(values[0])
            return values[0]
        except HTTPException:
            raise

    @model_validator(mode="before")
    @classmethod
    def federation_backend_as_string(cls, data: Any) -> Any:
        """currently eodag can only handle one provider -> use first entry in federation:backends list"""
        federation_backends = data.get("federation:backends", None)
        if not federation_backends or not isinstance(federation_backends, list) or len(federation_backends) == 0:
            data.pop("federation:backends", None)
            return data

        if isinstance(federation_backends[0], str):
            data["federation:backends"] = federation_backends[0]
            return data
        else:
            raise ValueError("federation:backends should be a string")
