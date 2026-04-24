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
import os
from typing import TYPE_CHECKING

from eodag import EODataAccessGateway
from eodag.api.collection import CollectionsDict
from eodag.databases.base import Database
from eodag.utils.exceptions import (
    RequestError,
    TimeOutError,
)
from eodag.utils.requests import fetch_json
from stac_fastapi.eodag.config import get_settings

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


def _build_database() -> Database | None:
    """Build the EODAG database backend according to settings.

    Returns ``None`` to let ``EODataAccessGateway`` fall back to its default
    SQLite backend. For the ``postgresql`` backend, a libpq connection string
    is built from the standard ``PG*`` environment variables (``PGHOST``,
    ``PGPORT``, ``PGUSER``, ``PGDATABASE``, ``PGPASSWORD``); any variable that
    is unset is omitted, letting libpq apply its own defaults.
    """
    settings = get_settings()
    if settings.database_type != "postgresql":
        return None

    try:
        from psycopg.conninfo import make_conninfo

        from stac_fastapi.eodag.databases.postgresql import PostgreSQLDatabase
    except ImportError as e:
        raise ImportError(
            "The 'postgresql' extra is required to use the PostgreSQL backend. "
            "Install it with: pip install stac-fastapi-eodag[postgresql]"
        ) from e

    pg_env_to_kwarg = {
        "PGHOST": "host",
        "PGPORT": "port",
        "PGUSER": "user",
        "PGDATABASE": "dbname",
        "PGPASSWORD": "password",
    }
    kwargs = {kwarg: os.environ[env] for env, kwarg in pg_env_to_kwarg.items() if os.getenv(env)}
    conninfo = make_conninfo(**kwargs)

    return PostgreSQLDatabase(conninfo=conninfo)


def init_dag(app: FastAPI) -> None:
    """Init EODataAccessGateway server instance, pre-running all time consuming tasks"""
    dag = EODataAccessGateway(db=_build_database())

    ext_stac_collections = fetch_external_stac_collections(dag.list_collections())

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
