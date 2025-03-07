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
"""properties for extensions."""

from typing import Annotated, Any, Optional, Union

import attr
from eodag.api.product.metadata_mapping import (
    OFFLINE_STATUS,
    ONLINE_STATUS,
    STAGING_STATUS,
)
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
)

from stac_fastapi.eodag.utils import str2liststr


@attr.s
class BaseStacExtension:
    """Abstract base class for defining STAC extensions."""

    FIELDS: Optional[type[BaseModel]] = None

    schema_href: str = attr.ib(default=None)

    field_name_prefix: Optional[str] = attr.ib(default=None)

    def __attrs_post_init__(self) -> None:
        """Add serialization validation_alias to extension properties
        and extension metadata to the field.
        """
        if self.field_name_prefix:
            fields: dict[str, Any] = getattr(self.FIELDS, "model_fields", {})
            for k, v in fields.items():
                v.serialization_alias = f"{self.field_name_prefix}:{k}"
                v.metadata.insert(0, {"extension": self.__class__.__name__})


class SarFields(BaseModel):
    """
    https://github.com/stac-extensions/sar#item-properties-or-asset-fields
    """

    instrument_mode: Optional[str] = Field(None, validation_alias="sensorMode")
    frequency_band: Optional[str] = Field(None, validation_alias="dopplerFrequency")
    center_frequency: Optional[float] = Field(None)
    polarizations: Annotated[
        Optional[Union[str, list[str]]],
        BeforeValidator(str2liststr),
    ] = Field(None, validation_alias="polarizationChannels")  # TODO: EODAG split string by "," to get this list
    resolution_range: Optional[float] = Field(None)
    resolution_azimuth: Optional[float] = Field(None)
    pixel_spacing_range: Optional[float] = Field(None)
    pixel_spacing_azimuth: Optional[float] = Field(None)
    looks_range: Optional[int] = Field(None)
    looks_azimuth: Optional[int] = Field(None)
    looks_equivalent_number: Optional[float] = Field(None)
    observation_direction: Optional[str] = Field(None)


@attr.s
class SarExtension(BaseStacExtension):
    """STAC SAR extension."""

    FIELDS = SarFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/sar/v1.0.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="sar")


class SatelliteFields(BaseModel):
    """
    https://github.com/stac-extensions/sat#item-properties
    """

    platform_international_designator: Optional[str] = Field(None, validation_alias="platform_international_designator")
    orbit_state: Optional[str] = Field(None, validation_alias="orbitDirection")
    absolute_orbit: Optional[int] = Field(None, validation_alias="orbitNumber")
    relative_orbit: Optional[int] = Field(None, validation_alias="relativeOrbitNumber")
    anx_datetime: Optional[str] = Field(None)


@attr.s
class SatelliteExtension(BaseStacExtension):
    """STAC Satellite extension."""

    FIELDS = SatelliteFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/sat/v1.0.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="sat")


class TimestampFields(BaseModel):
    """
    https://github.com/stac-extensions/timestamps#item-properties
    """

    published: Optional[str] = Field(None, validation_alias="publicationDate")
    unpublished: Optional[str] = Field(None)
    expires: Optional[str] = Field(None)


@attr.s
class TimestampExtension(BaseStacExtension):
    """STAC timestamp extension"""

    FIELDS = TimestampFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/timestamps/v1.0.0/schema.json")


class ProcessingFields(BaseModel):
    """
    https://github.com/stac-extensions/processing#item-properties
    """

    expression: Optional[dict[str, Any]] = Field(None)
    lineage: Optional[str] = Field(None)
    level: Optional[str] = Field(None, validation_alias="processingLevel")
    facility: Optional[str] = Field(None)
    software: Optional[dict[str, str]] = Field(None)


@attr.s
class ProcessingExtension(BaseStacExtension):
    """STAC processing extension."""

    FIELDS = ProcessingFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/processing/v1.0.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="processing")


class ViewGeometryFields(BaseModel):
    """
    https://github.com/stac-extensions/view#item-properties
    """

    off_nadir: Optional[float] = Field(None)
    incidence_angle: Optional[float] = Field(None)
    azimuth: Optional[float] = Field(None)
    sun_azimuth: Optional[float] = Field(None, validation_alias="illuminationAzimuthAngle")
    sun_elevation: Optional[float] = Field(None, validation_alias="illuminationElevationAngle")


@attr.s
class ViewGeometryExtension(BaseStacExtension):
    """STAC ViewGeometry extension."""

    FIELDS = ViewGeometryFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/view/v1.0.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="view")


class ElectroOpticalFields(BaseModel):
    """
    https://github.com/stac-extensions/eo#item-properties
    """

    cloud_cover: Optional[float] = Field(None, validation_alias="cloudCover")
    snow_cover: Optional[float] = Field(None, validation_alias="snowCover")
    bands: Optional[list[dict[str, Union[str, int]]]] = Field(None)


@attr.s
class ElectroOpticalExtension(BaseStacExtension):
    """STAC ElectroOptical extension."""

    FIELDS = ElectroOpticalFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/eo/v1.0.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="eo")


class ScientificCitationFields(BaseModel):
    """
    https://github.com/stac-extensions/scientific#item-properties
    """

    doi: Optional[str] = Field(None)
    citation: Optional[str] = Field(None)
    publications: Optional[list[dict[str, str]]] = Field(None)


@attr.s
class ScientificCitationExtension(BaseStacExtension):
    """STAC scientific extension."""

    FIELDS = ScientificCitationFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/scientific/v1.0.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="sci")


class ProductFields(BaseModel):
    """
    https://github.com/stac-extensions/product#fields
    """

    type: Optional[str] = Field(None, validation_alias="productType")
    timeliness: Optional[str] = Field(None)
    timeliness_category: Optional[str] = Field(None)


@attr.s
class ProductExtension(BaseStacExtension):
    """STAC product extension."""

    FIELDS = ProductFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/product/v0.1.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="product")


STATUS_STAC_MATCHING = {ONLINE_STATUS: "succeeded", STAGING_STATUS: "shipping", OFFLINE_STATUS: "orderable"}


class StorageFields(BaseModel):
    """
    https://github.com/stac-extensions/storage#fields
    """

    platform: Optional[str] = Field(default=None)
    region: Optional[str] = Field(default=None)
    requester_pays: Optional[bool] = Field(default=None)
    tier: Optional[str] = Field(default=None, validation_alias="storageStatus")

    @field_validator("tier")
    @classmethod
    def tier_to_stac(cls, v: Optional[str]) -> str:
        """Convert tier from EODAG naming to STAC"""
        return STATUS_STAC_MATCHING[v or OFFLINE_STATUS]


@attr.s
class StorageExtension(BaseStacExtension):
    """STAC product extension."""

    FIELDS = StorageFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/storage/v1.0.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="storage")


class OrderFields(BaseModel):
    """
    https://github.com/stac-extensions/order#fields
    """

    status: Optional[str] = Field(default=None)
    id: Optional[str] = Field(default=None, validation_alias="orderId")
    date: Optional[bool] = Field(default=None)


@attr.s
class OrderExtension(BaseStacExtension):
    """STAC product extension."""

    FIELDS = OrderFields

    schema_href: str = attr.ib(default="https://stac-extensions.github.io/order/v1.1.0/schema.json")
    field_name_prefix: Optional[str] = attr.ib(default="order")


class FederationFields(BaseModel):
    """
    https://github.com/Open-EO/openeo-api/tree/master/extensions/federation
    """

    backends: Optional[str] = Field(default=None, validation_alias="provider")


@attr.s
class FederationExtension(BaseStacExtension):
    """STAC federation extension."""

    FIELDS = FederationFields

    schema_href: str = attr.ib(default="https://api.openeo.org/extensions/federation/0.1.0")
    field_name_prefix: Optional[str] = attr.ib(default="federation")
