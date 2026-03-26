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

from eodag import EODataAccessGateway
from eodag.api.collection import CollectionsDict
from eodag.utils.exceptions import (
    RequestError,
    TimeOutError,
)
from eodag.utils.requests import fetch_json

if TYPE_CHECKING:
    from typing import Any

    from fastapi import FastAPI

    from eodag.api.collection import CollectionsDict, CollectionsList

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
        file_path = getattr(collection, "eodag_stac_collection", None)
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
    dag = EODataAccessGateway()

    ext_stac_collections = fetch_external_stac_collections(
        dag.list_collections()
    )

    # update eodag collections config from external stac collections
    collections = {}
    for c in dag.list_collections():
        if ext_coll := ext_stac_collections.get(c.id):
            collection = ext_coll
            collection["id"] = c._id
            collection["alias"] = c.id
            collections[c._id] = collection

    dag.db.upsert_collections(CollectionsDict.from_configs(collections))

    # pre-build search plugins
    for provider in dag.providers:
        next(dag._plugins_manager.get_search_plugins(provider=provider))

    app.state.dag = dag
