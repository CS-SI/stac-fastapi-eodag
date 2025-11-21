# -*- coding: utf-8 -*-
# Copyright 2024, CS GROUP - France, https://www.cs-soprasteria.com
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
"""Initialize EODAG"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from stac_pydantic.collection import Extent, SpatialExtent, TimeInterval

from eodag import EODataAccessGateway
from eodag.api.collection import CollectionsList
from eodag.utils.exceptions import (
    RequestError,
    TimeOutError,
)
from eodag.utils.requests import fetch_json
from stac_fastapi.eodag.config import get_settings

if TYPE_CHECKING:
    from typing import Any, Union

    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def fetch_external_stac_collections(
    collections: CollectionsList,
) -> dict[str, dict[str, Any]]:
    """Load external STAC collections

    :param collections: detailed product types dict list
    :return: dict of external STAC collections indexed by product type ID
    """
    ext_stac_collections: dict[str, dict[str, Any]] = {}

    for collection in collections:
        file_path = getattr(collection, "stac_collection", None)
        if not file_path:
            continue
        logger.info(f"Fetching external STAC collection for {collection.id}")

        try:
            ext_stac_collection = fetch_json(file_path)
        except (RequestError, TimeOutError) as e:
            logger.debug(e)
            logger.warning(
                f"Could not read remote external STAC collection from {file_path}",
            )
            ext_stac_collection = {}

        ext_stac_collections[collection.id] = ext_stac_collection
    return ext_stac_collections


def init_dag(app: FastAPI) -> None:
    """Init EODataAccessGateway server instance, pre-running all time consuming tasks"""
    settings = get_settings()

    dag = EODataAccessGateway()

    ext_stac_collections = fetch_external_stac_collections(
        dag.list_collections(fetch_providers=settings.fetch_providers)
    )

    app.state.ext_stac_collections = ext_stac_collections

    # update eodag collections config form external stac collections
    for p, p_f in dag.collections_config.items():
        for key in (p, getattr(p_f, "alias", None)):
            if key is None:
                continue
            ext_col = ext_stac_collections.get(key)
            if not ext_col:
                continue

            platform: Union[str, list[str]] = ext_col.get("summaries", {}).get("platform")
            constellation: Union[str, list[str]] = ext_col.get("summaries", {}).get("constellation")
            instruments: Union[str, list[str]] = ext_col.get("summaries", {}).get("instruments")
            processing_level: Union[str, list[str]] = ext_col.get("summaries", {}).get("processing:level")
            if isinstance(platform, list):
                platform = ",".join(platform)
            if isinstance(constellation, list):
                constellation = ",".join(constellation)
            if isinstance(processing_level, list):
                processing_level = ",".join(processing_level)
            ext_extent = ext_col["extent"]
            temporal_ext = TimeInterval(**ext_extent.get("temporal", [[None, None]]))
            spatial_ext = SpatialExtent(**ext_extent.get("spatial", {"bbox": [[-180.0, -90.0, 180.0, 90.0]]}))

            update_fields: dict[str, Any] = {
                "title": p_f.title or ext_col.get("title"),
                "description": p_f.description or ext_col["description"],
                "keywords": ext_col.get("keywords"),
                "instruments": p_f.instruments or instruments,
                "platform": p_f.platform or platform,
                "constellation": p_f.constellation or constellation,
                "processing_level": p_f.processing_level or processing_level,
                "license": ext_col["license"],
                "extent": Extent(temporal=temporal_ext, spatial=spatial_ext),
            }
            clean = {k: v for k, v in update_fields.items() if v is not None}
            for field, value in clean.items():
                setattr(p_f, field, value)

    # pre-build search plugins
    for provider in dag.available_providers():
        next(dag._plugins_manager.get_search_plugins(provider=provider))

    app.state.dag = dag
