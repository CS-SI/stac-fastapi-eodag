"""STAC item properties."""

from typing import Any, Optional

import attr

from stac_fastapi.eodag.extensions.item_properties import (
    ElectroOpticalExtension,
    ItemPropertiesExtension,
    ProcessingExtension,
    SarExtension,
    SatelliteExtension,
    ScientificCitationExtension,
    TimestampExtension,
    ViewGeometryExtension,
)
from stac_fastapi.eodag.models.item_properties_fields import FieldsItemProperties


@attr.s
class ItemProperties:
    """STAC item properties"""

    FIELDS = FieldsItemProperties

    extensions: Optional[list[ItemPropertiesExtension]] = attr.ib(
        default=[
            SarExtension(),
            SatelliteExtension(),
            TimestampExtension(),
            ProcessingExtension(),
            ViewGeometryExtension(),
            ElectroOpticalExtension(),
            ScientificCitationExtension(),
        ]
    )

    product_props: dict[str, Any] = attr.ib(default=None)

    def create_properties(self) -> tuple[dict[str, Any], list]:
        """Make properties for STAC item."""
        extension_schemas = []
        properties = self.FIELDS.model_validate(self.product_props).model_dump(
            exclude_none=True
        )
        for ext in self.extensions:
            ext_props = ext.FIELDS.model_validate(self.product_props).model_dump(
                exclude_none=True
            )
            if ext.field_name_prefix:
                ext_props = {
                    ext.field_name_prefix + key: value for key, value in ext_props.items()
                }
            if ext_props:
                extension_schemas.append(ext.schema_href)
                properties.update(ext_props)
        return properties, extension_schemas

    def get_properties(self) -> tuple[dict[str, Any], list]:
        return self.create_properties()
