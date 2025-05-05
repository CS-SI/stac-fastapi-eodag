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
"""Get Queryables."""

from typing import Any, Optional, cast

import attr
from fastapi import Request
from pydantic import BaseModel, ConfigDict, create_model
from stac_fastapi.extensions.core.filter.client import AsyncBaseFiltersClient
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url

from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.eodag_types.queryables import QueryablesGetParams
from stac_fastapi.eodag.errors import UnsupportedProductType
from stac_fastapi.eodag.models.stac_metadata import CommonStacMetadata

COMMON_QUERYABLES_PROPERTIES = {
    "id": {
        "title": "Provider ID",
        "description": "Provider item ID",
        "type": "string",
        "minLength": 1,
    },
    "collection": {
        "title": "Collection ID",
        "description": "The ID of the STAC Collection this Item references to.",
        "type": "string",
        "minLength": 1,
    },
    "geometry": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://geojson.org/schema/Geometry.json",
        "title": "GeoJSON Geometry",
        "oneOf": [
            {
                "title": "GeoJSON Point",
                "type": "object",
                "required": ["type", "coordinates"],
                "properties": {
                    "type": {"type": "string", "enum": ["Point"]},
                    "coordinates": {"type": "array", "minItems": 2, "items": {"type": "number"}},
                    "bbox": {"type": "array", "minItems": 4, "items": {"type": "number"}},
                },
            },
            {
                "title": "GeoJSON LineString",
                "type": "object",
                "required": ["type", "coordinates"],
                "properties": {
                    "type": {"type": "string", "enum": ["LineString"]},
                    "coordinates": {
                        "type": "array",
                        "minItems": 2,
                        "items": {"type": "array", "minItems": 2, "items": {"type": "number"}},
                    },
                    "bbox": {"type": "array", "minItems": 4, "items": {"type": "number"}},
                },
            },
            {
                "title": "GeoJSON Polygon",
                "type": "object",
                "required": ["type", "coordinates"],
                "properties": {
                    "type": {"type": "string", "enum": ["Polygon"]},
                    "coordinates": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "minItems": 4,
                            "items": {"type": "array", "minItems": 2, "items": {"type": "number"}},
                        },
                    },
                    "bbox": {"type": "array", "minItems": 4, "items": {"type": "number"}},
                },
            },
            {
                "title": "GeoJSON MultiPoint",
                "type": "object",
                "required": ["type", "coordinates"],
                "properties": {
                    "type": {"type": "string", "enum": ["MultiPoint"]},
                    "coordinates": {
                        "type": "array",
                        "items": {"type": "array", "minItems": 2, "items": {"type": "number"}},
                    },
                    "bbox": {"type": "array", "minItems": 4, "items": {"type": "number"}},
                },
            },
            {
                "title": "GeoJSON MultiLineString",
                "type": "object",
                "required": ["type", "coordinates"],
                "properties": {
                    "type": {"type": "string", "enum": ["MultiLineString"]},
                    "coordinates": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "items": {"type": "array", "minItems": 2, "items": {"type": "number"}},
                        },
                    },
                    "bbox": {"type": "array", "minItems": 4, "items": {"type": "number"}},
                },
            },
            {
                "title": "GeoJSON MultiPolygon",
                "type": "object",
                "required": ["type", "coordinates"],
                "properties": {
                    "type": {"type": "string", "enum": ["MultiPolygon"]},
                    "coordinates": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "minItems": 4,
                                "items": {"type": "array", "minItems": 2, "items": {"type": "number"}},
                            },
                        },
                    },
                    "bbox": {"type": "array", "minItems": 4, "items": {"type": "number"}},
                },
            },
        ],
    },
    "datetime": {
        "title": "Date and Time",
        "description": "The searchable date/time of the assets, in UTC (Formatted in RFC 3339) ",
        "type": ["string", "null"],
        "format": "date-time",
        "pattern": "(\\+00:00|Z)$",
    },
}


@attr.s
class FiltersClient(AsyncBaseFiltersClient):
    """Defines a pattern for implementing the STAC filter extension."""

    stac_metadata_model: type[CommonStacMetadata] = attr.ib(default=CommonStacMetadata)

    async def get_queryables(
        self,
        request: Request,
        collection_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Get the queryables available for the given collection_id.

        If collection_id is None, returns the intersection of all
        queryables over all collections.

        This base implementation returns a blank queryable schema. This is not allowed
        under OGC CQL but it is allowed by the STAC API Filter Extension
        https://github.com/radiantearth/stac-api-spec/tree/master/fragments/filter#queryables
        """
        params: dict[str, list[Any]] = {}
        for k, v in request.query_params.multi_items():
            params.setdefault(k, []).append(v)

        # parameter provider is deprecated
        providers = params.pop("provider", [None])
        federation_backends = params.pop("federation:backends", [None])

        # validate params and transform to eodag params
        validated_params_model = QueryablesGetParams.model_validate(
            {
                **{"provider": federation_backends[0] or providers[0], "collection": collection_id},
                **params,
            }
        )
        validated_params = validated_params_model.model_dump(exclude_none=True, by_alias=True)
        eodag_params = {self.stac_metadata_model.to_eodag(param): validated_params[param] for param in validated_params}
        # get queryables from eodag
        try:
            eodag_queryables = request.app.state.dag.list_queryables(**eodag_params)
        except UnsupportedProductType as err:
            raise NotFoundError(err) from err

        if "start" in eodag_queryables:
            start_queryable = eodag_queryables.pop("start")
            eodag_queryables["startTimeFromAscendingNode"] = start_queryable
        if "end" in eodag_queryables:
            end_queryable = eodag_queryables.pop("end")
            eodag_queryables["completionTimeFromAscendingNode"] = end_queryable

        base_url = get_base_url(request)
        stac_fastapi_title = get_settings().stac_fastapi_title

        queryables_model = cast(
            BaseModel,
            create_model(
                "Queryables",
                **eodag_queryables,
                __config__=ConfigDict(
                    protected_namespaces=(),
                    json_schema_extra={
                        "$schema": "https://json-schema.org/draft/2019-09/schema",
                        "$id": f"{base_url}/queryables",
                        "type": "object",
                        "title": f"Queryables for {stac_fastapi_title}.",
                        "description": f"Queryable names for the {stac_fastapi_title}.",
                        "additionalProperties": bool(not collection_id),
                    },
                    arbitrary_types_allowed=True,
                ),
            ),
        )
        queryables = queryables_model.model_json_schema()
        properties = queryables["properties"]
        required = queryables.get("required", [])

        for k, field in self.stac_metadata_model.model_fields.items():
            if field.validation_alias in properties:
                properties[field.serialization_alias or k] = properties[field.validation_alias]
                del properties[field.validation_alias]
            if field.validation_alias in required:
                required.remove(field.validation_alias)
                required.append(field.serialization_alias or k)

        # Only datetime is kept in queryables
        properties.pop("end_datetime", None)

        for _, value in properties.items():
            if "default" in value and value["default"] is None:
                del value["default"]

        for pk, pv in COMMON_QUERYABLES_PROPERTIES.items():
            if pk in properties:
                properties[pk] = pv

        return queryables
