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

    FIELDS = None

    schema_href: str = attr.ib(default=None)

    field_name_prefix: str | None = attr.ib(default=None)

    def __attrs_post_init__(self):
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

    instrument_mode: str | None = Field(None, validation_alias="sensorMode")
    frequency_band: str | None = Field(None, validation_alias="dopplerFrequency")
    center_frequency: float | None = Field(None)
    polarizations: Annotated[
        Optional[Union[str, list[str]]],
        BeforeValidator(str2liststr),
    ] = Field(
        None, validation_alias="polarizationChannels"
    )  # TODO: EODAG split string by "," to get this list
    resolution_range: float | None = Field(None)
    resolution_azimuth: float | None = Field(None)
    pixel_spacing_range: float | None = Field(None)
    pixel_spacing_azimuth: float | None = Field(None)
    looks_range: int | None = Field(None)
    looks_azimuth: int | None = Field(None)
    looks_equivalent_number: float | None = Field(None)
    observation_direction: str | None = Field(None)


@attr.s
class SarExtension(BaseStacExtension):
    """STAC SAR extension."""

    FIELDS = SarFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/sar/v1.0.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="sar")


class SatelliteFields(BaseModel):
    """
    https://github.com/stac-extensions/sat#item-properties
    """

    platform_international_designator: str | None = Field(
        None, validation_alias="platform_international_designator"
    )
    orbit_state: str | None = Field(None, validation_alias="orbitDirection")
    absolute_orbit: int | None = Field(None, validation_alias="orbitNumber")
    relative_orbit: int | None = Field(None, validation_alias="relativeOrbitNumber")
    anx_datetime: str | None = Field(None)


@attr.s
class SatelliteExtension(BaseStacExtension):
    """STAC Satellite extension."""

    FIELDS = SatelliteFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/sat/v1.0.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="sat")


class TimestampFields(BaseModel):
    """
    https://github.com/stac-extensions/timestamps#item-properties
    """

    published: str | None = Field(None, validation_alias="publicationDate")
    unpublished: str | None = Field(None)
    expires: str | None = Field(None)


@attr.s
class TimestampExtension(BaseStacExtension):
    """STAC timestamp extension"""

    FIELDS = TimestampFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/timestamps/v1.0.0/schema.json"
    )


class ProcessingFields(BaseModel):
    """
    https://github.com/stac-extensions/processing#item-properties
    """

    expression: dict[str, Any] = Field(None)
    lineage: str | None = Field(None)
    level: str | None = Field(None, validation_alias="processingLevel")
    facility: str | None = Field(None)
    software: dict[str, str] | None = Field(None)


@attr.s
class ProcessingExtension(BaseStacExtension):
    """STAC processing extension."""

    FIELDS = ProcessingFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/processing/v1.0.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="processing")


class ViewGeometryFields(BaseModel):
    """
    https://github.com/stac-extensions/view#item-properties
    """

    off_nadir: float | None = Field(None)
    incidence_angle: float | None = Field(None)
    azimuth: float | None = Field(None)
    sun_azimuth: float | None = Field(None, validation_alias="illuminationAzimuthAngle")
    sun_elevation: float | None = Field(
        None, validation_alias="illuminationElevationAngle"
    )


@attr.s
class ViewGeometryExtension(BaseStacExtension):
    """STAC ViewGeometry extension."""

    FIELDS = ViewGeometryFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/view/v1.0.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="view")


class ElectroOpticalFields(BaseModel):
    """
    https://github.com/stac-extensions/eo#item-properties
    """

    cloud_cover: float | None = Field(None, validation_alias="cloudCover")
    snow_cover: float | None = Field(None, validation_alias="snowCover")
    bands: list[dict[str, str | int]] | None = Field(None)


@attr.s
class ElectroOpticalExtension(BaseStacExtension):
    """STAC ElectroOptical extension."""

    FIELDS = ElectroOpticalFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/eo/v1.0.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="eo")


class ScientificCitationFields(BaseModel):
    """
    https://github.com/stac-extensions/scientific#item-properties
    """

    doi: str | None = Field(None)
    citation: str | None = Field(None)
    publications: list[dict[str, str]] | None = Field(None)


@attr.s
class ScientificCitationExtension(BaseStacExtension):
    """STAC scientific extension."""

    FIELDS = ScientificCitationFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/scientific/v1.0.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="sci")


class ProductFields(BaseModel):
    """
    https://github.com/stac-extensions/product#fields
    """

    type: str | None = Field(None)
    timeliness: str | None = Field(None)
    timeliness_category: str | None = Field(None)


@attr.s
class ProductExtension(BaseStacExtension):
    """STAC product extension."""

    FIELDS = ProductFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/product/v0.1.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="product")


STATUS_STAC_MATCHING = {
    ONLINE_STATUS: "succeeded",
    STAGING_STATUS: "shipping",
    OFFLINE_STATUS: "orderable"
}


class StorageFields(BaseModel):
    """
    https://github.com/stac-extensions/storage#fields
    """

    platform: str | None = Field(default=None)
    region: str | None = Field(default=None)
    requester_pays: bool | None = Field(default=None)
    tier: str | None = Field(default=None, validation_alias="storageStatus")

    @field_validator("tier")
    @classmethod
    def tier_to_stac(cls, v: str | None) -> str:
        """Convert tier from EODAG naming to STAC"""
        return STATUS_STAC_MATCHING[v or OFFLINE_STATUS]


@attr.s
class StorageExtension(BaseStacExtension):
    """STAC product extension."""

    FIELDS = StorageFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/storage/v1.0.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="storage")


class OrderFields(BaseModel):
    """
    https://github.com/stac-extensions/order#fields
    """

    status: str | None = Field(default=None)
    id: str | None = Field(default=None, validation_alias="orderId")
    date: bool | None = Field(default=None)


@attr.s
class OrderExtension(BaseStacExtension):
    """STAC product extension."""

    FIELDS = OrderFields

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/order/v1.1.0/schema.json"
    )
    field_name_prefix: str | None = attr.ib(default="order")
