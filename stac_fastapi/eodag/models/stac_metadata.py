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

from typing import Any, Optional

import attr
from fastapi import Request
from pydantic._internal._model_construction import ModelMetaclass

from eodag.types.stac_metadata import CommonStacMetadata, _get_conformance_classes
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
