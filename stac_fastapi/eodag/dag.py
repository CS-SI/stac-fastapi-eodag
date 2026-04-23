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
from stac_fastapi.eodag.config import get_settings

if TYPE_CHECKING:
    from typing import Any, Optional

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


def get_providers_status(collections_list: CollectionsList) -> dict[str, dict[str, Any]]:
    """Get the status of all providers based on their collections' status.

    :param collections_list: list of EODAG collections
    :return: Dictionary of providers' status indexed by provider ID
    """
    settings = get_settings()
    online_threshold = settings.provider_online_status_threshold
    # the key of providers_status is the provider ID
    providers_status: dict[str, dict[str, Any]] = {}

    def _get_last_check(status_1: dict[str, Any], status_2: dict[str, Any], key: str) -> Optional[str]:
        """Get the most recent check date between two status dictionaries

        The comparision handle possible `None` values in the dates.

        :param status_1: First status dictionary
        :param status_2: Second status dictionary
        :param key: Key to check in the status dictionaries (e.g. "last_status_check" or "last_successful_check")
        :return: Most recent check date as string, or None if not available in both dictionaries
        """
        check_1 = status_1.get(key)
        check_2 = status_2.get(key)
        if check_1 and check_2:
            return max(check_1, check_2)
        elif check_1:
            return check_1
        elif check_2:
            return check_2
        else:
            return None

    # count how many online/offline collections for each provider and keep the last check dates
    for collection in collections_list:
        if not getattr(collection, "federation", None):
            continue
        for provider_id, status in collection.federation.items():
            d = {"online": 0, "offline": 0, "last_status_check": None, "last_successful_check": None}
            ps = providers_status.setdefault(provider_id, d)
            ps["last_status_check"] = _get_last_check(ps, status, "last_status_check")
            ps["last_successful_check"] = _get_last_check(ps, status, "last_successful_check")
            if status["status"] == "online":
                ps["online"] += 1
            else:
                ps["offline"] += 1

    # determine provider's status based on online/offline collections count and threshold
    ret_providers_status = {}
    for provider_id, status in providers_status.items():
        online = status["online"]
        offline = status["offline"]
        total = online + offline
        if total == 0:
            provider_status = "offline"
        elif online / total >= online_threshold:
            provider_status = "online"
        else:
            provider_status = "offline"
        ret_providers_status[provider_id] = {
            "status": provider_status,
            "last_status_check": status["last_status_check"],
            "last_successful_check": status["last_successful_check"],
        }

    return ret_providers_status


def init_dag(app: FastAPI) -> None:
    """Init EODataAccessGateway server instance, pre-running all time consuming tasks"""
    dag = EODataAccessGateway()

    ext_stac_collections = fetch_external_stac_collections(dag.list_collections())

    # update eodag collections config from external stac collections
    collections = {}
    status = {}
    for c in dag.list_collections():
        if ext_coll := ext_stac_collections.get(c.id):
            collection = ext_coll
            collection["id"] = c._id
            collection["alias"] = c.id
            if federation := collection.pop("federation", None):
                status[c._id] = federation
            collections[c._id] = collection

    dag.db.upsert_collections(CollectionsDict.from_configs(collections))

    # store status in a separate DB column to avoid federation to be overwritten by subsequent upsert_collections() calls
    dag.db.set_status(status)

    # store providers status in app state
    app.state.providers_status = get_providers_status(dag.list_collections())

    # pre-build search plugins
    for provider in dag.providers:
        next(dag._plugins_manager.get_search_plugins(provider=provider))

    app.state.dag = dag
