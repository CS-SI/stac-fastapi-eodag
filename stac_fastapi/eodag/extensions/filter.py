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

import asyncio
from typing import Any, Literal, Optional, cast, get_args, get_origin

import attr
from fastapi import Request
from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, create_model
from stac_fastapi.extensions.core.filter.client import AsyncBaseFiltersClient
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url

from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.eodag_types.queryables import QueryablesGetParams
from stac_fastapi.eodag.errors import UnsupportedCollection
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
        eodag_params = self._get_eodag_params(request, collection_id)

        # get queryables from eodag
        try:
            eodag_queryables = await asyncio.to_thread(request.app.state.dag.list_queryables, **eodag_params)
        except UnsupportedCollection as err:
            raise NotFoundError(err) from err

        if "start" in eodag_queryables:
            start_queryable = eodag_queryables.pop("start")
            eodag_queryables["start_datetime"] = start_queryable
        if "end" in eodag_queryables:
            end_queryable = eodag_queryables.pop("end")
            eodag_queryables["end_datetime"] = end_queryable

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
                        "$id": base_url
                        + (f"collections/{collection_id}/queryables" if collection_id else "queryables"),
                        "type": "object",
                        "title": f"STAC queryables for {stac_fastapi_title}.",
                        "description": f"Queryable names for {stac_fastapi_title}.",
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
                if (field.serialization_alias or k) != field.validation_alias:
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

    def _get_eodag_params(
        self,
        request: Request,
        collection_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return the EODAG parameters from the given HTTP Request.

        :param request: The request object.
        :param collection_id: The collection ID.
        :return: The EODAG parameters.
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

        # the parameters in eodag_params are all lists:
        # adapt them to use list or primitive type according to the collection queryables
        eodag_params_pc = {k: eodag_params[k] for k in ["provider", "collection"] if k in eodag_params}
        try:
            eodag_queryables = request.app.state.dag.list_queryables(**eodag_params_pc)
        except UnsupportedCollection as err:
            raise NotFoundError(err) from err

        for queryables_key, annotation in eodag_queryables.items():
            if queryables_key in ("provider", "collection"):
                continue
            param_args = get_args(annotation)
            base_type = get_origin(param_args[0])
            if base_type is None:
                base_type = param_args[0]
            field_info = param_args[1]

            # get the aliases of queryable_key
            validation_alias = field_info.validation_alias
            aliases: list[str]
            if isinstance(validation_alias, str):
                aliases = [queryables_key, validation_alias]
            elif isinstance(validation_alias, AliasChoices):
                # e.g. names == ['ecmwf_data_format', 'ecmwf:data_format', 'data_format']
                if any(not isinstance(c, str) for c in validation_alias.choices):
                    # currently only choices of type string are used by EODAG
                    raise NotImplementedError(
                        f"Error for stac name {queryables_key}: "
                        "only AliasChoices of type string are handled to get field aliases"
                    )
                choices: list[str] = [str(c) for c in validation_alias.choices]
                aliases = [queryables_key, *choices]
            elif isinstance(validation_alias, AliasPath):
                # currently AliasPath is not used by EODAG
                raise NotImplementedError(
                    f"Error for stac name {queryables_key}: AliasPath is not currently handled to get field aliases"
                )
            elif validation_alias is None:
                aliases = [queryables_key]
            else:
                raise NotImplementedError(
                    f"Error for stac name {queryables_key}: validation alias no supported: {validation_alias}"
                )

            # check if any of the aliases is in eodag_params
            eodag_key = next((n for n in aliases if n in eodag_params.keys()), None)
            if not eodag_key:
                # queryable_key is not in eodag_params: skip
                continue

            # adapt the value
            if base_type is (Literal, str):
                if isinstance(eodag_params[eodag_key], list):
                    # convert list to single value
                    eodag_params[eodag_key] = eodag_params[eodag_key][0]
            elif base_type in (tuple, list):
                if not isinstance(eodag_params[eodag_key], list):
                    # convert single value to list
                    eodag_params[eodag_key] = [eodag_params[eodag_key]]
            else:
                raise NotImplementedError(f"Error for stac name {queryables_key}: type not supported: {param_args[0]}")
        return eodag_params
