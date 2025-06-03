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
"""EODAG STAC API configuration"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Union

from pydantic import Field
from pydantic.functional_validators import BeforeValidator
from stac_fastapi.types.config import ApiSettings

from stac_fastapi.eodag.utils import str2liststr


class Settings(ApiSettings):
    """EODAG Server config"""

    debug: bool = False

    keep_origin_url: bool = Field(
        default=False,
        description=("Keep origin as alternate URL when data-download extension is enabled."),
    )
    origin_url_blacklist: Annotated[Union[str, list[str]], BeforeValidator(str2liststr)] = Field(
        default=[],
        description=("Hide from clients items assets' origin URLs starting with URLs from the list"),
    )

    auto_order_whitelist: Annotated[Union[str, list[str]], BeforeValidator(str2liststr)] = Field(
        default=["wekeo_main",],
        description=("Do the order at the same time as the download"),
    )

    fetch_providers: bool = Field(default=False, description="Fetch additional collections from all providers.")

    download_base_url: str = Field(
        default="",
        description="base url to be used for download link",
        pattern=r"(http|https):\/\/[\w:.-]+\/",
        validate_default=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get settings"""
    return Settings()
