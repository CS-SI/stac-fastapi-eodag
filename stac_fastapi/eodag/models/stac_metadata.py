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

from collections.abc import Callable
from datetime import datetime as dt
from typing import Any, ClassVar, Optional, Union, cast

import attr
from fastapi import Request
from pydantic import (
    AliasChoices,
    AliasPath,
    Field,
    model_validator,
)
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.fields import FieldInfo
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.stac import Item
from stac_pydantic.api.extensions.sort import SortDirections, SortExtension
from stac_pydantic.api.version import STAC_API_VERSION
from stac_pydantic.item import ItemProperties
from stac_pydantic.shared import Provider
from typing_extensions import Self

from eodag.api.product._product import EOProduct
from eodag.utils import deepcopy
from stac_fastapi.eodag.config import Settings, get_settings
from stac_fastapi.eodag.constants import ITEM_PROPERTIES_EXCLUDE
from stac_fastapi.eodag.extensions.stac import (
    BaseStacExtension,
)
from stac_fastapi.eodag.models.links import ItemLinks


class CommonStacMetadata(ItemProperties):
    """Common STAC properties."""

    # TODO: replace dt by stac_pydantic.shared.UtcDatetime.
    # Requires timezone to be set in EODAG datetime properties
    # Tested with EFAS FORECAST
    datetime: Optional[dt] = Field(default=None, validation_alias="startTimeFromAscendingNode")
    start_datetime: Optional[dt] = Field(
        default=None, validation_alias="startTimeFromAscendingNode"
    )  # TODO do not set if start = end
    end_datetime: Optional[dt] = Field(
        default=None, validation_alias="completionTimeFromAscendingNode"
    )  # TODO do not set if start = end
    created: Optional[dt] = Field(default=None, validation_alias="creationDate")
    updated: Optional[dt] = Field(default=None, validation_alias="modificationDate")
    platform: Optional[str] = Field(default=None, validation_alias="platformSerialIdentifier")
    instruments: Optional[list[str]] = Field(
        default=None, validation_alias="instruments"
    )  # TODO EODAG has instrument a string with "," separated instruments
    constellation: Optional[str] = Field(default=None, validation_alias="platform")
    providers: Optional[list[Provider]] = None
    gsd: Optional[float] = Field(default=None, validation_alias="resolution", gt=0)

    _conformance_classes: ClassVar[dict[str, str]]
    get_conformance_classes: ClassVar[Callable[[Any], list[str]]]

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

    @classmethod
    def _create_to_eodag_map(cls) -> dict[str, Optional[Union[str, AliasChoices, AliasPath]]]:
        """Create mapping to convert fields from STAC to EODAG"""
        return {v.serialization_alias or k: v.validation_alias for k, v in cls.model_fields.items()}

    @classmethod
    def to_eodag(cls, field_name: str) -> str:
        """Convert a STAC parameter to its matching EODAG name.

        Note: ``ids`` STAC parameter is not recognized since we are dealing with item properties
        """
        field_dict: dict[str, Optional[Union[str, AliasChoices, AliasPath]]] = {
            stac_name: eodag_name
            for stac_name, eodag_name in cls._create_to_eodag_map().items()
            if field_name == stac_name
        }
        if field_dict:
            if field_dict[field_name] is None:
                return field_name
            if isinstance(field_dict[field_name], (AliasChoices, AliasPath)):
                raise NotImplementedError(
                    f"Error for stac name {field_name}: AliasChoices and AliasPath are not currently handled to"
                    "convert stac names to eodag names"
                )
            return field_dict[field_name]  # type: ignore
        return field_name

    @classmethod
    def to_stac(cls, field_name: str) -> str:
        """Convert an EODAG parameter to its matching STAC name.

        Note: ``ids`` STAC parameter is not recognized since we are dealing with item properties
        """
        field_dict: dict[str, Optional[Union[str, AliasChoices, AliasPath]]] = {
            stac_name: eodag_name
            for stac_name, eodag_name in cls._create_to_eodag_map().items()
            if field_name == eodag_name
        }
        if field_dict:
            return list(field_dict.keys())[0]
        return field_name


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


def create_stac_item(
    product: EOProduct,
    model: type[CommonStacMetadata],
    extension_is_enabled: Callable[[str], bool],
    request: Request,
    request_json: Optional[Any] = None,
) -> Item:
    """Create a STAC item from an EODAG product"""
    if product.product_type is None:
        raise NotFoundError("A STAC item can not be created from an EODAG EOProduct without collection")

    settings: Settings = get_settings()
    feature = Item(
        assets={},
        id=product.properties["title"],
        geometry=product.geometry.__geo_interface__,
        bbox=product.geometry.bounds,
        collection=product.product_type,
        stac_version=STAC_API_VERSION,
    )

    stac_extensions: set[str] = set()

    asset_proxy_url = (
        (
            get_base_url(request) + f"data/{product.provider}/{feature['collection']}/{feature['id']}"  # type: ignore
        )
        if extension_is_enabled("DataDownload")  # self.extension_is_enabled("DataDownload")
        else None
    )

    for k, v in product.assets.items():
        # TODO: download extension with origin link (make it optional ?)
        asset_model = model.model_validate(v)
        stac_extensions.update(asset_model.get_conformance_classes())
        feature["assets"][k] = asset_model.model_dump(exclude_none=True)

        if asset_proxy_url:
            origin = deepcopy(feature["assets"][k])
            feature["assets"][k]["href"] = asset_proxy_url + "/" + k

            if settings.keep_origin_url:
                feature["assets"][k]["alternate"] = {"origin": origin}

    # TODO: remove downloadLink asset after EODAG assets rework
    if download_link := product.properties.get("downloadLink"):
        origin_href = download_link
        if asset_proxy_url:
            download_link = asset_proxy_url + "/downloadLink"

        feature["assets"]["downloadLink"] = {
            "title": "Download link",
            "href": download_link,
            # TODO: download link is not always a ZIP archive
            "type": "application/zip",
        }

        if settings.keep_origin_url:
            feature["assets"]["downloadLink"]["alternate"] = {
                "origin": {
                    "title": "Origin asset link",
                    "href": origin_href,
                    # TODO: download link is not always a ZIP archive
                    "type": "application/zip",
                },
            }

    feature_model = model.model_validate({**product.properties, **{"federation:backends": [product.provider]}})
    stac_extensions.update(feature_model.get_conformance_classes())
    feature["properties"] = feature_model.model_dump(exclude_none=True, exclude=ITEM_PROPERTIES_EXCLUDE)

    feature["stac_extensions"] = list(stac_extensions)

    feature["links"] = ItemLinks(
        collection_id=feature["collection"],
        item_id=feature["id"],
        order_link=product.properties.get("orderLink"),
        federation_backend=feature["properties"]["federation:backends"][0],
        dc_qs=product.properties.get("_dc_qs"),
        request=request,
    ).get_links(extra_links=feature.get("links"), request_json=request_json)

    return feature


def _get_conformance_classes(self) -> list[str]:
    """Extract list of conformance classes from set fields metadata"""
    conformance_classes: set[str] = set()

    for f in self.model_fields_set:
        mf = self.model_fields.get(f)
        if not mf or not isinstance(mf, FieldInfo) or not mf.metadata:
            continue
        extension = next(
            (cast(str, m["extension"]) for m in mf.metadata if isinstance(m, dict) and "extension" in m),
            None,
        )
        if c := self._conformance_classes.get(extension, None):
            conformance_classes.add(c)

    return list(conformance_classes)


def get_sortby_to_post(get_sortby: Optional[list[str]]) -> Optional[list[SortExtension]]:
    """Convert sortby filter parameter GET syntax to POST syntax"""
    if not get_sortby:
        return None
    post_sortby: list[SortExtension] = []
    for sortby_param in get_sortby:
        sortby_param = sortby_param.strip()
        direction = "desc" if sortby_param.startswith("-") else "asc"
        field = sortby_param.lstrip("+-")
        post_sortby.append(SortExtension(field=field, direction=SortDirections(direction)))
    return post_sortby
