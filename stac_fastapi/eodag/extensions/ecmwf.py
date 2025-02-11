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
"""ECMWF STAC extension."""

from typing import Optional

import attr
from pydantic import BaseModel, Field

from stac_fastapi.eodag.extensions.stac import BaseStacExtension


class EcmwfItemProperties(BaseModel):
    """
    STAC extension from ECMWF MARS keywords.

    https://confluence.ecmwf.int/display/UDOC/Keywords+in+MARS+and+Dissemination+requests
    """

    accuracy: Optional[str] = Field(default=None)
    anoffset: Optional[str] = Field(default=None)
    area: Optional[str] = Field(default=None)
    bitmap: Optional[str] = Field(default=None)
    block: Optional[str] = Field(default=None)
    channel: Optional[str] = Field(default=None)
    ecmwf_class: Optional[str] = Field(default=None, alias="class")
    database: Optional[str] = Field(default=None)
    date: Optional[str] = Field(default=None)
    diagnostic: Optional[str] = Field(default=None)
    direction: Optional[str] = Field(default=None)
    domain: Optional[str] = Field(default=None)
    duplicates: Optional[str] = Field(default=None)
    expect: Optional[str] = Field(default=None)
    expver: Optional[str] = Field(default=None)
    fcmonth: Optional[str] = Field(default=None)
    fcperiod: Optional[str] = Field(default=None)
    fieldset: Optional[str] = Field(default=None)
    filter: Optional[str] = Field(default=None)
    format: Optional[str] = Field(default=None)
    frame: Optional[str] = Field(default=None)
    frequency: Optional[str] = Field(default=None)
    grid: Optional[str] = Field(default=None)
    hdate: Optional[str] = Field(default=None)
    ident: Optional[str] = Field(default=None)
    interpolation: Optional[str] = Field(default=None)
    intgrid: Optional[str] = Field(default=None)
    iteration: Optional[str] = Field(default=None)
    latitude: Optional[str] = Field(default=None)
    levelist: Optional[str] = Field(default=None)
    levtype: Optional[str] = Field(default=None)
    longitude: Optional[str] = Field(default=None)
    lsm: Optional[str] = Field(default=None)
    method: Optional[str] = Field(default=None)
    number: Optional[str] = Field(default=None)
    obsgroup: Optional[str] = Field(default=None)
    obstype: Optional[str] = Field(default=None)
    origin: Optional[str] = Field(default=None)
    packing: Optional[str] = Field(default=None)
    padding: Optional[str] = Field(default=None)
    param: Optional[str] = Field(default=None)
    priority: Optional[str] = Field(default=None)
    product: Optional[str] = Field(default=None)
    range: Optional[str] = Field(default=None)
    refdate: Optional[str] = Field(default=None)
    reference: Optional[str] = Field(default=None)
    reportype: Optional[str] = Field(default=None)
    repres: Optional[str] = Field(default=None)
    resol: Optional[str] = Field(default=None)
    rotation: Optional[str] = Field(default=None)
    section: Optional[str] = Field(default=None)
    source: Optional[str] = Field(default=None)
    step: Optional[str] = Field(default=None)
    stream: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)
    target: Optional[str] = Field(default=None)
    time: Optional[str] = Field(default=None)
    truncation: Optional[str] = Field(default=None)
    ecmwf_type: Optional[str] = Field(default=None)
    use: Optional[str] = Field(default=None)


@attr.s
class EcmwfExtension(BaseStacExtension):
    """STAC SAR extension."""

    FIELDS = EcmwfItemProperties

    field_name_prefix: Optional[str] = attr.ib(default="ecmwf")
