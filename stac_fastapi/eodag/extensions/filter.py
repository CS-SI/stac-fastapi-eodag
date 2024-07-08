"""Get Queryables."""

from typing import Any, Dict, Optional, Type, cast

import attr
from eodag.utils.exceptions import UnsupportedProductType
from fastapi import Request
from pydantic import BaseModel, ConfigDict, create_model
from stac_fastapi.extensions.core.filter.client import AsyncBaseFiltersClient
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url

from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.models.stac_metadata import CommonStacMetadata

COMMON_QUERYABLES_PROPERTIES = {
    "id" : {
      "description" : "ID",
      "$ref": "https://schemas.stacspec.org/v1.0.0/item-spec/json-schema/item.json#/id"
    },
    "collection" : {
      "description" : "Collection",
      "$ref": "https://schemas.stacspec.org/v1.0.0/item-spec/json-schema/item.json#/collection"
    },
    "geometry" : {
      "description" : "Geometry",
      "$ref": "https://schemas.stacspec.org/v1.0.0/item-spec/json-schema/item.json#/geometry"
    },
    "datetime" : {
      "description" : "Datetime",
      "$ref": "https://schemas.stacspec.org/v1.0.0/item-spec/json-schema/datetime.json#/properties/datetime"
    }
}


@attr.s
class FiltersClient(AsyncBaseFiltersClient):
    """Defines a pattern for implementing the STAC filter extension."""

    stac_metadata_model: Type[BaseModel] = attr.ib(default=CommonStacMetadata)

    async def get_queryables(
        self,
        request: Request,
        collection_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get the queryables available for the given collection_id.

        If collection_id is None, returns the intersection of all
        queryables over all collections.
        This base implementation returns a blank queryable schema. This is not allowed
        under OGC CQL but it is allowed by the STAC API Filter Extension
        https://github.com/radiantearth/stac-api-spec/tree/master/fragments/filter#queryables
        """
        # TODO: add support for query extension instead of native query params like in legacy eodag?
        try:
            eodag_queryables = request.app.state.dag.list_queryables(
                productType=collection_id
            )
        except UnsupportedProductType as err:
            raise NotFoundError(err) from err

        base_url = get_base_url(request)
        stac_fastapi_title = get_settings().stac_fastapi_title

        queryables_model = cast(BaseModel, create_model(
            "Queryables",
            **eodag_queryables,
            __config__=ConfigDict(
                json_schema_extra=
                {
                    "$schema": "https://json-schema.org/draft/2019-09/schema",
                    "$id": f"{base_url}/queryables",
                    "type": "object",
                    "title": f"Queryables for {stac_fastapi_title}.",
                    "description": f"Queryable names for the {stac_fastapi_title}.",
                    "additionalProperties": bool(not collection_id)
                }
            )
        ))
        queryables = queryables_model.model_json_schema()
        properties = cast(dict[str, Any], queryables["properties"])

        for k, v in self.stac_metadata_model.model_fields.items():
            if v.validation_alias in properties:
                properties[v.serialization_alias or k] = properties[v.validation_alias]
                del properties[v.validation_alias]

        # Only datetime is kept in queryables
        properties.pop("end_datetime", None)

        for k, v in COMMON_QUERYABLES_PROPERTIES.items():
            if k in properties:
                properties[k] = v

        return queryables
