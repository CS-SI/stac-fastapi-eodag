"""property fields."""
# -*- coding: utf-8 -*-
# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
#
# This file is part of EODAG project
#     https://www.github.com/CS-SI/EODAG
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
from datetime import datetime as dt
from typing import List, Optional, Set, Type, cast

import attr
from pydantic import BaseModel, Field, model_validator
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.fields import FieldInfo
from stac_pydantic.item import ItemProperties
from stac_pydantic.shared import Provider
from typing_extensions import Self

from stac_fastapi.eodag.extensions.stac import (
    BaseStacExtension,
)


class CommonStacMetadata(ItemProperties):
    """Common STAC properties."""

    # TODO: replace dt by stac_pydantic.shared.UtcDatetime.
    # Requires timezone to be set in EODAG datetime properties
    # Tested with EFAS FORECAST
    datetime: dt | None = Field(
        default=None, validation_alias="startTimeFromAscendingNode"
    )
    start_datetime: dt | None = Field(
        default=None, validation_alias="startTimeFromAscendingNode"
    )  # TODO do not set if start = end
    end_datetime: dt | None = Field(
        default=None, validation_alias="completionTimeFromAscendingNode"
    )  # TODO do not set if start = end
    created: dt | None = Field(default=None, validation_alias="creationDate")
    updated: dt | None = Field(default=None, validation_alias="modificationDate")
    platform: str | None = Field(
        default=None, validation_alias="platformSerialIdentifier"
    )
    instruments: list[str] | None = Field(
        default=None, validation_alias="instruments"
    )  # TODO EODAG has instrument a string with "," separated instruments
    constellation: str | None = Field(default=None, validation_alias="platform")
    providers: list[Provider] | None = None
    gsd: float | None = Field(default=None, validation_alias="resolution", gt=0)

    @model_validator(mode="after")
    def validate_datetime_or_start_end(self) -> Self:
        """disable validation of datetime.
        This model is used for properties conversion not validation.
        """
        return self

    @model_validator(mode="after")
    def validate_start_end(self) -> Self:
        """disable validation of datetime.
        This model is used for properties conversion not validation.
        """
        return self


def create_stac_metadata_model(
    extensions: Optional[List[BaseStacExtension]] = None,
    base_model: type[CommonStacMetadata] = CommonStacMetadata,
) -> Type[BaseModel]:
    """Create a pydantic model to validate item properties."""
    extension_models: list[ModelMetaclass] = []

    extensions = extensions or []

    # Check extensions for additional parameters to include
    for extension in extensions:
        if extension_model := extension.FIELDS:
            extension_models.append(extension_model)

    models = [base_model] + extension_models

    model = attr.make_class("StacMetadata", attrs={}, bases=tuple(models))
    model._conformance_classes = {e.__class__.__name__: e.schema_href for e in extensions}
    model.get_conformance_classes = _get_conformance_classes
    return model


def _get_conformance_classes(self: BaseModel) -> List[str]:
    """Extract list of conformance classes from set fields metadata"""
    conformance_classes: Set[str] = set()

    for f in self.model_fields_set:
        mf = self.model_fields.get(f)
        if not mf or type(mf) != FieldInfo or not mf.metadata:
            continue
        extension = next(
            (
                cast(str, m["extension"])
                for m in mf.metadata
                if isinstance(m, dict) and "extension" in m
            ),
            None,
        )
        if c := self._conformance_classes.get(extension, None):
            conformance_classes.add(c)

    return list(conformance_classes)
