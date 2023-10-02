import attr
from typing import Optional
from pydantic import BaseModel
from stac_fastapi.eodag.models.item_properties_fields import (
    FieldsSarItemProperties,
    FieldsSatelliteItemProperties,
    FieldsTimestampItemProperties,
    FieldsProcessingItemProperties,
    FieldsViewGeometryItemProperties,
    FieldsElectroOpticalItemProperties,
    FieldsScientificCitationItemProperties,
)


@attr.s
class ItemPropertiesExtension:
    """Abstract base class for defining Item properties extensions."""

    FIELDS: BaseModel = None

    schema_href: str = attr.ib(default=None)

    field_name_prefix: Optional[str] = attr.ib(default=None)


@attr.s
class SarExtension(ItemPropertiesExtension):
    FIELDS = FieldsSarItemProperties

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/sar/v1.0.0/schema.json"
    )
    field_name_prefix: Optional[str] = attr.ib(default="sar")


@attr.s
class SatelliteExtension(ItemPropertiesExtension):
    FIELDS = FieldsSatelliteItemProperties

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/sat/v1.0.0/schema.json"
    )
    field_name_prefix: Optional[str] = attr.ib(default="sat")


@attr.s
class TimestampExtension(ItemPropertiesExtension):
    FIELDS = FieldsTimestampItemProperties

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/timestamps/v1.0.0/schema.json"
    )


@attr.s
class ProcessingExtension(ItemPropertiesExtension):
    FIELDS = FieldsProcessingItemProperties

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/processing/v1.0.0/schema.json"
    )
    field_name_prefix: Optional[str] = attr.ib(default="processing")


@attr.s
class ViewGeometryExtension(ItemPropertiesExtension):
    FIELDS = FieldsViewGeometryItemProperties

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/view/v1.0.0/schema.json"
    )
    field_name_prefix: Optional[str] = attr.ib(default="view")


@attr.s
class ElectroOpticalExtension(ItemPropertiesExtension):
    FIELDS = FieldsElectroOpticalItemProperties

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/eo/v1.0.0/schema.json"
    )
    field_name_prefix: Optional[str] = attr.ib(default="eo")


@attr.s
class ScientificCitationExtension(ItemPropertiesExtension):
    FIELDS = FieldsScientificCitationItemProperties

    schema_href: str = attr.ib(
        default="https://stac-extensions.github.io/scientific/v1.0.0/schema.json"
    )
    field_name_prefix: Optional[str] = attr.ib(default="sci")
