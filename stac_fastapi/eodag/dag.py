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

from eodag import EODataAccessGateway, setup_logging
from eodag.utils import obj_md5sum
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
    product_types: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Load external STAC collections

    :param product_types: detailed product types dict list
    :return: dict of external STAC collections indexed by product type ID
    """
    ext_stac_collections: dict[str, dict[str, Any]] = {}

    for product_type in product_types:
        file_path = product_type.get("stacCollection")
        if not file_path:
            continue
        logger.info(f"Fetching external STAC collection for {product_type['ID']}")

        try:
            ext_stac_collection = fetch_json(file_path)
        except (RequestError, TimeOutError) as e:
            logger.debug(e)
            logger.warning(
                f"Could not read remote external STAC collection from {file_path}",
            )
            ext_stac_collection = {}

        ext_stac_collections[product_type["ID"]] = ext_stac_collection
    return ext_stac_collections


def init_dag(app: FastAPI) -> None:
    """Init EODataAccessGateway server instance, pre-running all time consuming tasks"""
    settings = get_settings()

    setup_logging(3 if settings.debug else 2, no_progress_bar=True)

    dag = EODataAccessGateway()

    ext_stac_collections = fetch_external_stac_collections(
        dag.list_product_types(fetch_providers=settings.fetch_providers)
    )

    app.state.ext_stac_collections = ext_stac_collections

    # update eodag product_types config form external stac collections
    for p, p_f in dag.product_types_config.source.items():
        for key in (p, p_f.get("alias")):
            if key is None:
                continue
            ext_col = ext_stac_collections.get(key)
            if not ext_col:
                continue
            platform: Union[str, list[str]] = ext_col.get("summaries", {}).get("platform")
            constellation: Union[str, list[str]] = ext_col.get("summaries", {}).get("constellation")
            # Check if platform or constellation are lists
            # and join them into a string if they are
            if isinstance(platform, list):
                platform = ",".join(platform)
            if isinstance(constellation, list):
                constellation = ",".join(constellation)

            update_fields = {
                "title": ext_col.get("title"),
                "abstract": ext_col["description"],
                "keywords": ext_col.get("keywords"),
                "instrument": ",".join(ext_col.get("summaries", {}).get("instruments", [])),
                "platform": constellation,
                "platformSerialIdentifier": platform,
                "processingLevel": ",".join(ext_col.get("summaries", {}).get("processing:level", [])),
                "license": ext_col["license"],
                "missionStartDate": ext_col["extent"]["temporal"]["interval"][0][0],
                "missionEndDate": ext_col["extent"]["temporal"]["interval"][-1][1],
            }
            clean = {k: v for k, v in update_fields.items() if v}
            p_f.update(clean)

    dag.product_types_config_md5 = obj_md5sum(dag.product_types_config.source)

    dag.build_index()

    # pre-build search plugins
    for provider in dag.available_providers():
        next(dag._plugins_manager.get_search_plugins(provider=provider))

    app.state.dag = dag
