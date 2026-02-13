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
"""property fields."""

from typing import Any, Optional, cast

import attr
from fastapi import Request
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.fields import FieldInfo

from eodag.types.stac_metadata import CommonStacMetadata
from stac_fastapi.eodag.extensions.stac import (
    BaseStacExtension,
)


def create_stac_metadata_model(
    extensions: Optional[list[BaseStacExtension]] = None,
    base_model: type[CommonStacMetadata] = CommonStacMetadata,
) -> type[CommonStacMetadata]:
    """Create a pydantic model to validate item properties."""
    extension_models: list[ModelMetaclass] = []

    extensions = extensions or []

    # Check extensions for additional parameters to include
    for extension in extensions:
        if extension_model := extension.FIELDS:
            extension_models.append(extension_model)

    models = [base_model] + extension_models

    model = attr.make_class(
        "StacMetadata",
        attrs={},
        bases=tuple(models),
        class_body={
            "_conformance_classes": {e.__class__.__name__: e.schema_href for e in extensions},
            "get_conformance_classes": _get_conformance_classes,
        },
    )
    return model


def get_federation_backend_dict(request: Request, provider_name: str) -> dict[str, Any]:
    """Generate Federation backend dict

    :param request: FastAPI request
    :param provider_name: provider name
    :return: Federation backend dictionary
    """
    provider = next(
        p for p in request.app.state.dag.providers.values() if provider_name in [p.name, getattr(p, "group", None)]
    )
    return {
        "title": provider.group or provider.name,
        "description": provider.title,
        "url": provider.url,
    }


def _get_conformance_classes(self) -> list[str]:
    """Extract list of conformance classes from set fields metadata"""
    conformance_classes: set[str] = set()

    model_fields_by_alias = {
        field_info.serialization_alias: field_info
        for name, field_info in self.model_fields.items()
        if field_info.serialization_alias
    }

    for f in self.model_fields_set:
        mf = model_fields_by_alias.get(f) or self.model_fields.get(f)
        if not mf or not isinstance(mf, FieldInfo) or not mf.metadata:
            continue
        extension = next(
            (cast(str, m["extension"]) for m in mf.metadata if isinstance(m, dict) and "extension" in m),
            None,
        )
        if c := self._conformance_classes.get(extension, None):
            conformance_classes.add(c)

    return list(conformance_classes)
