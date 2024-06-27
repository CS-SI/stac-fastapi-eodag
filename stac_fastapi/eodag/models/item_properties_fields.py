"""property fields."""

from datetime import datetime as dt
from typing import Annotated, Optional, Union

from pydantic import BaseModel, BeforeValidator, Field, confloat
from stac_pydantic import ItemProperties as BaseFieldsItemProperties
from stac_pydantic.shared import Provider

from stac_fastapi.eodag.utils import str2liststr


class FieldsSarItemProperties(BaseModel):
    """
    https://github.com/stac-extensions/sar#item-properties-or-asset-fields
    """

    instrument_mode: Optional[str] = Field(None, alias="sensorMode")
    frequency_band: Optional[str] = Field(None, alias="dopplerFrequency")
    center_frequency: Optional[float] = Field(None, alias="center_frequency")
    polarizations: Annotated[
        Optional[Union[str, list[str]]],
        BeforeValidator(str2liststr),
    ] = Field(
        None, alias="polarizationMode"
    )  # TODO: EODAG split string by "," to get this list
    resolution_range: Optional[float] = Field(None, alias="resolution_range")
    resolution_azimuth: Optional[float] = Field(None, alias="resolution_azimuth")
    pixel_spacing_range: Optional[float] = Field(None, alias="pixel_spacing_range")
    pixel_spacing_azimuth: Optional[float] = Field(None, alias="pixel_spacing_azimuth")
    looks_range: Optional[int] = Field(None, alias="looks_range")
    looks_azimuth: Optional[int] = Field(None, alias="looks_azimuth")
    looks_equivalent_number: Optional[float] = Field(
        None, alias="looks_equivalent_number"
    )
    observation_direction: Optional[str] = Field(None, alias="observation_direction")


class FieldsSatelliteItemProperties(BaseModel):
    """
    https://github.com/stac-extensions/sat#item-properties
    """

    platform_international_designator: Optional[str] = Field(
        None, alias="platform_international_designator"
    )
    orbit_state: Optional[str] = Field(None, alias="orbitDirection")
    absolute_orbit: Optional[int] = Field(None, alias="orbitNumber")
    relative_orbit: Optional[int] = Field(None, alias="relativeOrbitNumber")
    anx_datetime: Optional[str] = Field(None, alias="anx_datetime")


class FieldsTimestampItemProperties(BaseModel):
    """
    https://github.com/stac-extensions/timestamps#item-properties
    """

    published: Optional[str] = Field(None, alias="publicationDate")
    unpublished: Optional[str] = Field(None, alias="unpublished")
    expires: Optional[str] = Field(None, alias="expires")


class FieldsProcessingItemProperties(BaseModel):
    """
    https://github.com/stac-extensions/processing#item-properties
    """

    expression: Optional[dict] = Field(None, alias="expression")
    lineage: Optional[str] = Field(None, alias="lineage")
    level: Optional[str] = Field(None, alias="processingLevel")
    facility: Optional[str] = Field(None, alias="facility")
    software: Optional[dict[str, str]] = Field(None, alias="software")


class FieldsViewGeometryItemProperties(BaseModel):
    """
    https://github.com/stac-extensions/view#item-properties
    """

    off_nadir: Optional[float] = Field(None, alias="off_nadir")
    incidence_angle: Optional[float] = Field(None, alias="incidence_angle")
    azimuth: Optional[float] = Field(None, alias="azimuth")
    sun_azimuth: Optional[float] = Field(None, alias="sun_azimuth")
    sun_elevation: Optional[float] = Field(None, alias="sun_elevation")


class FieldsElectroOpticalItemProperties(BaseModel):
    """
    https://github.com/stac-extensions/eo#item-properties
    """

    cloud_cover: Optional[float] = Field(None, alias="cloud_cover")
    snow_cover: Optional[float] = Field(None, alias="snow_cover")
    bands: Optional[list[dict]] = Field(None, alias="bands")


class FieldsScientificCitationItemProperties(BaseModel):
    """
    https://github.com/stac-extensions/scientific#item-properties
    """

    doi: Optional[str] = Field(None, alias="doi")
    citation: Optional[str] = Field(None, alias="citation")
    publications: Optional[list[dict]] = Field(None, alias="publications")


class FieldsItemProperties(BaseFieldsItemProperties):
    datetime: Union[dt, str] = Field(..., alias="startTimeFromAscendingNode")
    title: Optional[str] = Field(None, alias="title")
    description: Optional[str] = Field(None, alias="description")
    start_datetime: Optional[dt] = Field(
        None, alias="startTimeFromAscendingNode"
    )  # TODO do not set if start = end
    end_datetime: Optional[dt] = Field(
        None, alias="completionTimeFromAscendingNode"
    )  # TODO do not set if start = end
    created: Optional[dt] = Field(None, alias="creationDate")
    updated: Optional[dt] = Field(None, alias="modificationDate")
    platform: Optional[str] = Field(None, alias="platformSerialIdentifier")
    instruments: Optional[list[str]] = Field(
        None, alias="instruments"
    )  # TODO EODAG has instrument a string with "," separated instruments
    constellation: Optional[str] = Field(None, alias="platform")
    mission: Optional[str] = Field(None, alias="mission")
    providers: Optional[list[Provider]] = Field(None, alias="providers")
    gsd: Optional[confloat(gt=0)] = Field(None, alias="resolution")
