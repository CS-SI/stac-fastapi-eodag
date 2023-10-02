import attr
from typing import Optional, Any
from stac_fastapi.eodag.models.item_properties_fields import FieldsItemProperties
from stac_fastapi.eodag.extensions.item_properties import (
    ItemPropertiesExtension,
    SarExtension,
    SatelliteExtension,
    TimestampExtension,
    ProcessingExtension,
    ViewGeometryExtension,
    ElectroOpticalExtension,
    ScientificCitationExtension,
)


@attr.s
class ItemProperties:
    FIELDS = FieldsItemProperties

    extensions: Optional[list[ItemPropertiesExtension]] = attr.ib(
        default=[
            SarExtension,
            SatelliteExtension,
            TimestampExtension,
            ProcessingExtension,
            ViewGeometryExtension,
            ElectroOpticalExtension,
            ScientificCitationExtension,
        ]
    )

    product_props: dict[str, Any] = attr.ib(default=None)

    def create_properties(self) -> tuple[dict[str, Any], list]:
        extension_schemas = []
        properties = self.FIELDS.parse_obj(self.product_props).dict(exclude_none=True)
        for ext in self.extensions:
            ext_props = ext.FIELDS.parse_obj(self.product_props).dict(exclude_none=True)
            if ext.field_name_prefix:
                ext_props = {
                    ext.field_name_prefix + key: value
                    for key, value in ext_props.items()
                }
            if ext_props:
                extension_schemas.append(ext.schema_href)
                properties.update(ext_props)
        return properties, extension_schemas

    async def get_properties(self) -> tuple[dict[str, Any], list]:
        return self.create_properties()
