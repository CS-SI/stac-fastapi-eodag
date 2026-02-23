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
"""properties for extensions."""

from typing import Any, Optional

import attr
from pydantic import (
    BaseModel,
    Field,
)


@attr.s
class BaseStacExtension:
    """Abstract base class for defining STAC extensions."""

    FIELDS: Optional[type[BaseModel]] = None

    schema_href: str = attr.ib(default=None)

    field_name_prefix: Optional[str] = attr.ib(default=None)

    def __attrs_post_init__(self) -> None:
        """Add serialization validation_alias to extension properties
        and extension metadata to the field.
        """
        if self.field_name_prefix:
            fields: dict[str, Any] = getattr(self.FIELDS, "model_fields", {})
            for k, v in fields.items():
                if not v.serialization_alias:
                    v.serialization_alias = f"{self.field_name_prefix}:{k}"
                v.metadata.insert(0, {"extension": self.__class__.__name__})


class FederationFields(BaseModel):
    """
    https://github.com/Open-EO/openeo-api/tree/master/extensions/federation
    """

    backends: Optional[str] = Field(default=None, validation_alias="provider")


@attr.s
class FederationExtension(BaseStacExtension):
    """STAC federation extension."""

    FIELDS = FederationFields

    schema_href: str = attr.ib(default="https://api.openeo.org/extensions/federation/0.1.0")
    field_name_prefix: Optional[str] = attr.ib(default="federation")
