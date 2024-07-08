"""ECMWF STAC extension."""
import attr
from pydantic import BaseModel, Field

from stac_fastapi.eodag.extensions.stac import BaseStacExtension


class EcmwfItemProperties(BaseModel):
    """
    STAC extension from ECMWF MARS keywords.
    https://confluence.ecmwf.int/display/UDOC/Keywords+in+MARS+and+Dissemination+requests
    """
    accuracy: str| None = Field(default=None)
    anoffset: str | None = Field(default=None)
    area: str | None = Field(default=None)
    bitmap: str | None = Field(default=None)
    block: str | None = Field(default=None)
    channel: str | None = Field(default=None)
    ecmwf_class: str | None = Field(default=None, alias="class")
    database: str | None = Field(default=None)
    date: str | None = Field(default=None)
    diagnostic: str | None = Field(default=None)
    direction: str | None = Field(default=None)
    domain: str | None = Field(default=None)
    duplicates: str | None = Field(default=None)
    expect: str | None = Field(default=None)
    expver: str | None = Field(default=None)
    fcmonth: str | None = Field(default=None)
    fcperiod: str | None = Field(default=None)
    fieldset: str | None = Field(default=None)
    filter: str | None = Field(default=None)
    format: str | None = Field(default=None)
    frame: str | None = Field(default=None)
    frequency: str | None = Field(default=None)
    grid: str | None = Field(default=None)
    hdate: str | None = Field(default=None)
    ident: str | None = Field(default=None)
    interpolation: str | None = Field(default=None)
    intgrid: str | None = Field(default=None)
    iteration: str | None = Field(default=None)
    latitude: str | None = Field(default=None)
    levelist: str | None = Field(default=None)
    levtype: str | None = Field(default=None)
    longitude: str | None = Field(default=None)
    lsm: str | None = Field(default=None)
    method: str | None = Field(default=None)
    number: str | None = Field(default=None)
    obsgroup: str | None = Field(default=None)
    obstype: str | None = Field(default=None)
    origin: str | None = Field(default=None)
    packing: str | None = Field(default=None)
    padding: str | None = Field(default=None)
    param: str | None = Field(default=None)
    priority: str | None = Field(default=None)
    product: str | None = Field(default=None)
    range: str | None = Field(default=None)
    refdate: str | None = Field(default=None)
    reference: str | None = Field(default=None)
    reportype: str | None = Field(default=None)
    repres: str | None = Field(default=None)
    resol: str | None = Field(default=None)
    rotation: str | None = Field(default=None)
    section: str | None = Field(default=None)
    source: str | None = Field(default=None)
    step: str | None = Field(default=None)
    stream: str | None = Field(default=None)
    system: str | None = Field(default=None)
    target: str | None = Field(default=None)
    time: str | None = Field(default=None)
    truncation: str | None = Field(default=None)
    type: str | None = Field(default=None)
    use: str | None = Field(default=None)

@attr.s
class EcmwfExtension(BaseStacExtension):
    """STAC SAR extension."""

    FIELDS = EcmwfItemProperties

    field_name_prefix: str | None = attr.ib(default="ecmwf")
