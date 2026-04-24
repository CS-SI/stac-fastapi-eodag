# -*- coding: utf-8 -*-
# Copyright 2026, CS GROUP - France, https://www.csgroup.eu/
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
"""PostgreSQL backend for EODAG.

Connection parameters are read from the standard libpq environment variables:
``PGHOST``, ``PGPORT``, ``PGUSER``, ``PGDATABASE``, ``PGPASSWORD``.

Requirements (server-side):
- PostgreSQL >= 12 (for STORED generated columns)
- ``postgis`` extension (spatial types and indexes)
- ``unaccent`` extension (CQL2 ``accenti`` operator)

PostgreSQL always uses Write-Ahead Logging (WAL) internally; no client-side
configuration is needed.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional, Union, cast

import cql2
import orjson
import psycopg
from eodag.api.collection import Collection, CollectionsDict
from eodag.api.product.metadata_mapping import NOT_AVAILABLE
from eodag.databases.base import (
    Database,
    stac_search_to_where,
    stac_sortby_to_order_by,
)
from eodag.utils import (
    GENERIC_COLLECTION,
    PLUGINS_TOPIC_KEYS,
)
from eodag.utils.env import is_env_var_true
from psycopg import sql as pg_sql
from psycopg.rows import dict_row
from psycopg.types.json import JsonbDumper, set_json_dumps, set_json_loads

from stac_fastapi.eodag.databases.postgresql_cql2 import cql2_json_to_sql
from stac_fastapi.eodag.databases.postgresql_fts import stac_q_to_tsquery

if TYPE_CHECKING:
    from collections.abc import Sequence

    from eodag.config import ProviderConfig
    from psycopg.rows import DictRow
    from shapely.geometry.base import BaseGeometry

logger = logging.getLogger("eodag.databases.postgresql_database")


class PostgreSQLDatabase(Database):
    """Database backend backed by PostgreSQL (with PostGIS and unaccent).

    The connection is created from the standard libpq environment variables
    (``PGHOST``, ``PGPORT``, ``PGUSER``, ``PGDATABASE``, ``PGPASSWORD``).
    """

    _con: psycopg.Connection[Any]

    def __init__(self, conninfo: Optional[str] = None) -> None:
        """Initialize the database by creating a connection and preparing the schema.

        :param conninfo: Optional libpq connection string. When omitted (the
            default), connection parameters are read from the ``PG*``
            environment variables.

        :raises: :class:`~psycopg.Error` if the connection cannot be established
            or the schema initialisation fails.
        """
        # ``conninfo=""`` makes libpq use the standard PG* environment variables.
        # The connection is opened with dict_row factory so that execute() can
        # be called directly on the connection object.
        try:
            self._con = psycopg.connect(
                conninfo if conninfo is not None else "",
                autocommit=False,
                row_factory=dict_row,
            )
        except psycopg.Error as e:
            logger.error(
                "Failed to connect to PostgreSQL database "
                "(check PGHOST, PGPORT, PGUSER, PGDATABASE, PGPASSWORD "
                "environment variables or the supplied conninfo): %s",
                e,
            )
            raise

        _register_json_adapters(self._con)

        try:
            _ensure_extensions(self._con)
            create_collections_table(self._con)
            create_collections_federation_backends_table(self._con)
            create_federation_backends_table(self._con)
            self._con.commit()
        except Exception:
            if not self._con.closed:
                self._con.rollback()
            raise

    def close(self) -> None:
        """Close the database connection.

        No-op if the connection is already closed.
        """
        if self._con and not self._con.closed:
            self._con.close()

    # ------------------------------------------------------------------ utils
    def _execute(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> psycopg.Cursor[DictRow]:
        """Execute a SQL statement, rolling back the connection on failure.

        :param sql: SQL statement to execute.
        :param parameters: Sequence of parameters to bind to the statement.

        :raises: :class:`~psycopg.Error` if execution fails (the transaction is
            rolled back before re-raising).

        :returns: The cursor after execution.
        """
        try:
            return self._con.execute(sql, parameters)
        except psycopg.Error as e:
            self._con.rollback()
            raise e

    def _executemany(self, sql: str, parameters: Sequence[Sequence[Any]]) -> psycopg.Cursor[DictRow]:
        """Execute a SQL statement against many parameter sets.

        :param sql: SQL statement to execute repeatedly.
        :param parameters: Sequence of parameter sequences, one per execution.

        :raises: :class:`~psycopg.Error` if any execution fails (the transaction
            is rolled back before re-raising).

        :returns: The cursor after all executions.
        """
        try:
            cur = self._con.cursor()
            cur.executemany(sql, parameters)
            return cur
        except psycopg.Error as e:
            self._con.rollback()
            raise e

    # --------------------------------------------------------------- mutators
    def delete_collections(self, collection_ids: list[str]) -> None:
        """Remove collections and their federation backend configs from the database.

        Matches against both ``id`` and ``internal_id`` columns to handle aliases.

        :param collection_ids: List of collection IDs (or internal IDs) to delete.

        :raises ValueError: if ``collection_ids`` is empty.
        :raises: :class:`~psycopg.Error` if the database operation fails.
        """
        if not collection_ids:
            raise ValueError("collection_ids cannot be empty")

        match_clause = "(id = ANY(%s) OR internal_id = ANY(%s))"
        # Delete federation backend configs using internal_id lookup
        self._execute(
            "DELETE FROM collections_federation_backends WHERE collection_id IN "
            f"(SELECT internal_id FROM collections WHERE {match_clause})",
            (collection_ids, collection_ids),
        )
        self._execute(
            f"DELETE FROM collections WHERE {match_clause}",
            (collection_ids, collection_ids),
        )
        self._con.commit()

    def delete_collections_federation_backends(self, collection_ids: list[str]) -> None:
        """Remove collection entries from the collections_federation_backends table.

        :param collection_ids: List of collection internal IDs whose federation
            backend entries should be removed. No-op if the list is empty.

        :raises: :class:`~psycopg.Error` if the database operation fails.
        """
        if not collection_ids:
            return
        self._execute(
            "DELETE FROM collections_federation_backends WHERE collection_id = ANY(%s)",
            (collection_ids,),
        )
        self._con.commit()

    def upsert_collections(self, collections: CollectionsDict) -> None:
        """Add or update collections in the database.

        Collections with ID ``GENERIC_COLLECTION`` or ``GENERIC_PRODUCT_TYPE``
        are silently skipped.

        :param collections: Mapping of collection objects or dicts to upsert.

        :raises: :class:`~psycopg.Error` if the database operation fails.
        """

        def _get_id(c: Any) -> Optional[str]:
            if isinstance(c, Collection):
                return c.id
            return c.get("id") if isinstance(c, dict) else None

        rows = [
            (_collection_to_json(c),)
            for c in collections.values()
            if _get_id(c) not in (GENERIC_COLLECTION, "GENERIC_PRODUCT_TYPE")
        ]
        if not rows:
            return

        cur = self._executemany(
            """
            INSERT INTO collections (content) VALUES (%s)
            ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content;
            """,
            rows,
        )
        upserted = cur.rowcount
        self._con.commit()

        if upserted and upserted > 0:
            logger.debug(
                "%d collection(s) have been updated or added to the database",
                upserted,
            )

    def _upsert_federation_backends(
        self,
        fb_configs: list[tuple[str, dict[str, dict[str, Any]], int, dict[str, Any], bool]],
    ) -> None:
        """Add or update federation backend configs (providers) in the database.

        :param fb_configs: List of tuples ``(name, plugins_config, priority,
            metadata, enabled)`` describing each federation backend.

        :raises: :class:`~psycopg.Error` if the database operation fails.
        """
        if not fb_configs:
            return
        self._executemany(
            """
            INSERT INTO federation_backends (name, plugins_config, priority, metadata, enabled)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                plugins_config = EXCLUDED.plugins_config,
                priority = EXCLUDED.priority,
                metadata = EXCLUDED.metadata,
                enabled = EXCLUDED.enabled
            """,
            fb_configs,
        )
        logger.debug("Upserted %d federation backend(s)", len(fb_configs))

    def _upsert_collections_federation_backends(self, coll_fb_configs: list[tuple[str, str, dict[str, Any]]]) -> None:
        """Upsert collection-specific federation backend configs.

        :param coll_fb_configs: List of tuples ``(collection_id,
            federation_backend_name, plugins_config)`` to upsert.

        :raises: :class:`~psycopg.Error` if the database operation fails.
        """
        if not coll_fb_configs:
            return
        self._executemany(
            """
            INSERT INTO collections_federation_backends
                (collection_id, federation_backend_name, plugins_config)
            VALUES (%s, %s, %s)
            ON CONFLICT (collection_id, federation_backend_name) DO UPDATE SET
                plugins_config = EXCLUDED.plugins_config
            """,
            coll_fb_configs,
        )
        logger.debug("Upserted %d collection-provider config(s)", len(coll_fb_configs))

    def _refresh_collections_denorm(self, changed_fbs: list[str]) -> None:
        """Refresh the denormalized ``federation_backends`` and ``priority`` columns.

        Re-aggregates the ``federation_backends`` array and ``priority`` value for
        all collections linked to the given federation backends.

        :param changed_fbs: Names of federation backends whose collections should
            be refreshed. No-op if the list is empty.

        :raises: :class:`~psycopg.Error` if the database operation fails.
        """
        if not changed_fbs:
            return

        # Build a CTE that aggregates federation backends and max priority per
        # affected collection, then update those collections in a single pass.
        self._execute(
            """
            WITH affected AS (
                SELECT DISTINCT cfb.collection_id
                FROM collections_federation_backends cfb
                WHERE cfb.federation_backend_name = ANY(%s)
            ),
            agg AS (
                SELECT
                    cfb.collection_id,
                    COALESCE(
                        array_agg(fb.name ORDER BY fb.priority DESC, fb.name ASC),
                        ARRAY[]::text[]
                    ) AS federation_backends,
                    COALESCE(MAX(fb.priority), 0) AS priority
                FROM affected a
                JOIN collections_federation_backends cfb
                    ON cfb.collection_id = a.collection_id
                JOIN federation_backends fb
                    ON fb.name = cfb.federation_backend_name AND fb.enabled = TRUE
                GROUP BY cfb.collection_id
            )
            UPDATE collections c
            SET
                federation_backends = COALESCE(agg.federation_backends, ARRAY[]::text[]),
                priority = COALESCE(agg.priority, 0)
            FROM affected
            LEFT JOIN agg ON agg.collection_id = affected.collection_id
            WHERE c.internal_id = affected.collection_id;
            """,
            (changed_fbs,),
        )

    def upsert_fb_configs(self, configs: list[ProviderConfig]) -> None:
        """Add or update federation backend configs (providers) in the database.

        Processes each provider config to extract plugin settings and per-collection
        product configurations, then persists them atomically. In permissive mode
        (``EODAG_STRICT_COLLECTIONS`` not set), unknown collection IDs are created
        automatically.

        :param configs: List of provider configuration objects to persist.

        :raises: :class:`~psycopg.Error` if the database operation fails (the
            transaction is rolled back before re-raising).
        """
        federation_backend_configs: list[tuple[str, dict[str, dict[str, Any]], int, dict[str, Any], bool]] = []
        coll_fb_configs: list[tuple[str, str, dict[str, Any]]] = []
        changed_fbs: set[str] = set()
        known_collections = {coll["id"] for coll in self.collections_search(with_fbs_only=False)[0]} | {
            GENERIC_COLLECTION,
            "GENERIC_PRODUCT_TYPE",
        }
        strict_mode = is_env_var_true("EODAG_STRICT_COLLECTIONS")
        collections_to_add: list[Collection] = []

        def strip_credentials(plugin_conf: dict[str, Any]) -> dict[str, Any]:
            return {k: v for k, v in plugin_conf.items() if k != "credentials"}

        for config in configs:
            exclude_keys = set(PLUGINS_TOPIC_KEYS) | {
                "name",
                "priority",
                "enabled",
                "products",
            }
            metadata = {k: v for k, v in config.__dict__.items() if k not in exclude_keys}

            plugins_config: dict[str, dict[str, Any]] = {}
            for k in PLUGINS_TOPIC_KEYS:
                if val := getattr(config, k, None):
                    plugins_config[k] = strip_credentials(val.__dict__)

            federation_backend_configs.append(
                (
                    config.name,
                    plugins_config,
                    getattr(config, "priority", 0),
                    metadata,
                    config.enabled,
                )
            )

            topics_cfg: dict[str, dict[str, Any]] = {}
            products_cfg = getattr(config, "products", {})
            if getattr(config, "api", None):
                topics_cfg["api"] = products_cfg
            else:
                topics_cfg["search"] = products_cfg
                if products_download_cfg := getattr(getattr(config, "download", None), "products", None):
                    topics_cfg["download"] = products_download_cfg

            tmp: dict[str, dict[str, Any]] = defaultdict(lambda t=topics_cfg: {topic: None for topic in t})

            for topic, products_cfg in topics_cfg.items():
                for coll_id, cfg in products_cfg.items():
                    if strict_mode and coll_id not in known_collections:
                        continue
                    if coll_id not in known_collections:
                        collections_to_add.append(Collection(id=coll_id, title=coll_id, description=NOT_AVAILABLE))

                    tmp[coll_id][topic] = cfg

            for coll_id, cfg in tmp.items():
                coll_fb_configs.append((coll_id, config.name, cfg))

            changed_fbs.add(config.name)

        try:
            if collections_to_add:
                self.upsert_collections(CollectionsDict(collections_to_add))
                logger.debug(
                    "Collections permissive mode, %s added",
                    ", ".join(c.id for c in collections_to_add),
                )
            self._upsert_federation_backends(federation_backend_configs)
            self._upsert_collections_federation_backends(coll_fb_configs)
            self._refresh_collections_denorm(sorted(changed_fbs))
            self._con.commit()
        except Exception:
            if not self._con.closed:
                self._con.rollback()
            raise

    def set_priority(self, name: str, priority: int) -> None:
        """Set the priority of a federation backend.

        :param name: Name of the federation backend to update.
        :param priority: New priority value.

        :raises: :class:`~psycopg.Error` if the database operation fails (the
            transaction is rolled back before re-raising).
        """
        try:
            self._execute(
                "UPDATE federation_backends SET priority = %s WHERE name = %s",
                (priority, name),
            )
            self._refresh_collections_denorm([name])
            self._con.commit()
        except Exception:
            if not self._con.closed:
                self._con.rollback()
            raise

    # --------------------------------------------------------------- queries
    def collections_search(
        self,
        geometry: Optional[Union[str, dict[str, float], BaseGeometry]] = None,
        datetime: Optional[str] = None,
        limit: Optional[int] = None,
        q: Optional[str] = None,
        ids: Optional[list[str]] = None,
        federation_backends: Optional[list[str]] = None,
        cql2_text: Optional[str] = None,
        cql2_json: Optional[dict[str, Any]] = None,
        sortby: Optional[list[dict[str, str]]] = None,
        with_fbs_only: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search collections matching the given parameters.

        :param geometry: Optional spatial filter as a WKT string, a bounding-box
            dict, or a Shapely geometry.
        :param datetime: Optional temporal filter as an ISO 8601 datetime or
            interval (e.g. ``"2020-01-01/2020-12-31"``).
        :param limit: Maximum number of collections to return.
        :param q: Free-text search expression (STAC ``q`` syntax).
        :param ids: List of collection IDs to restrict results to.
        :param federation_backends: List of federation backend names to filter by.
        :param cql2_text: CQL2 text filter expression. Mutually exclusive with
            ``cql2_json``.
        :param cql2_json: CQL2 JSON filter expression. Mutually exclusive with
            ``cql2_text``.
        :param sortby: List of sort specifications, each a dict with ``field``
            and ``direction`` keys.
        :param with_fbs_only: If ``True`` (default), only return collections that
            have at least one federation backend assigned.

        :raises ValueError: if both ``cql2_text`` and ``cql2_json`` are provided.
        :raises: :class:`~psycopg.Error` if the database query fails.

        :returns: A tuple ``(collections, total)`` where ``collections`` is the
            list of matching collection dicts (each including a
            ``federation:backends`` key) and ``total`` is the total number of
            matching collections ignoring the ``limit``.
        """
        if cql2_text and cql2_json:
            raise ValueError("Cannot provide both cql2_text and cql2_json")

        if cql2_text:
            cql2_json = cql2.parse_text(cql2_text).to_json()

        where = stac_search_to_where(
            cql2_json_to_sql,
            geometry,
            datetime,
            ids,
            federation_backends,
            cql2_json,
        )

        from_clause = "FROM collections c"
        where_parts = [where, "c.federation_backends IS NOT NULL"] if with_fbs_only else [where]
        params: list[Any] = []
        order_terms: list[str] = []
        select_score = ""

        if q:
            ts_expr = stac_q_to_tsquery(q)
            if ts_expr:
                # Match against the precomputed weighted tsvector, ranked with
                # ``ts_rank_cd`` (ascending = best match first means we negate it).
                where_parts.append("c.tsv @@ to_tsquery('simple', %s)")
                params.append(ts_expr)

                select_score = ", ts_rank_cd(c.tsv, to_tsquery('simple', %s)) AS rank_score"
                params.insert(0, ts_expr)  # parameter for SELECT clause
                order_terms = ["rank_score DESC"]

        if sortby:
            order_terms = stac_sortby_to_order_by(sortby)

        order_terms.extend(["c.priority DESC NULLS LAST", "c.id ASC"])
        order_by = " ORDER BY " + ", ".join(order_terms)

        full_where = " AND ".join(where_parts)

        # Count uses only the WHERE-clause parameters, not the SELECT-clause one.
        count_params = list(params)
        if select_score:
            # The first parameter is the SELECT-clause tsquery; drop it for COUNT.
            count_params = count_params[1:]

        count_row = self._execute(
            f"SELECT COUNT(*) AS n {from_clause} WHERE {full_where}",
            count_params or None,
        ).fetchone()
        number_matched = cast(int, count_row["n"]) if count_row is not None else 0

        sql = (
            f"SELECT c.content AS content, "
            f"c.federation_backends AS federation_backends{select_score} "
            f"{from_clause} WHERE {full_where}{order_by}"
        )
        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        collections_list: list[dict[str, Any]] = []
        for row in self._execute(sql, params or None).fetchall():
            coll = _collection_from_json(row["content"])
            coll["federation:backends"] = row["federation_backends"]
            collections_list.append(coll)

        return collections_list, number_matched

    def get_federation_backends(
        self,
        names: Optional[set[str]] = None,
        enabled: Optional[bool] = None,
        fetchable: Optional[bool] = None,
        collection: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict[str, dict[str, Any]]:
        """Return federation backends according to filters.

        :param names: Restrict results to backends with these names.
        :param enabled: If ``True``, return only enabled backends; if ``False``,
            return only disabled ones; if ``None`` (default), return all.
        :param fetchable: If ``True``, return only backends whose metadata marks
            them as fetchable; if ``False``, return only non-fetchable ones; if
            ``None`` (default), return all.
        :param collection: If provided, restrict to backends linked to this
            collection ID.
        :param limit: Maximum number of backends to return.

        :raises: :class:`~psycopg.Error` if the database query fails.

        :returns: Dict mapping each backend name to a dict with ``priority``,
            ``enabled``, and ``metadata`` keys.
        """
        sql = "SELECT fb.name, fb.priority, fb.enabled, fb.metadata FROM federation_backends fb"
        where_clauses: list[str] = []
        params: list[Any] = []

        if collection:
            sql += (
                " INNER JOIN collections_federation_backends cfb "
                "ON fb.name = cfb.federation_backend_name AND cfb.collection_id = %s"
            )
            params.append(collection)

        if enabled is not None:
            where_clauses.append(f"{'NOT ' if not enabled else ''}fb.enabled")

        if fetchable is not None:
            cmp = "= TRUE" if fetchable else "IS DISTINCT FROM TRUE"
            where_clauses.append(f"(fb.metadata->>'fetchable')::boolean {cmp}")

        if names:
            where_clauses.append("fb.name = ANY(%s)")
            params.append(list(names))

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY fb.priority DESC, fb.name ASC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        rows = self._execute(sql, params or None).fetchall()

        return {
            row["name"]: {
                "priority": row["priority"],
                "enabled": bool(row["enabled"]),
                "metadata": row["metadata"] or {},
            }
            for row in rows
        }

    def get_fb_config(
        self,
        name: str,
        collections: set[str] | None = None,
    ) -> dict[str, Any]:
        """Get the federation backend config for a given provider and optional collection filter.

        :param name: Name of the federation backend to retrieve.
        :param collections: Optional set of collection IDs whose per-collection
            plugin config should be included in the returned dict.

        :raises KeyError: if the federation backend ``name`` is not found.
        :raises: :class:`~psycopg.Error` if the database query fails.

        :returns: Dict with the provider's merged plugin config, metadata,
            priority, enabled flag, and per-collection product configs.
        """
        collections = collections or set()

        if collections:
            cfb_filter_sql = "cfb.collection_id = ANY(%s)"
            cfb_params: tuple[Any, ...] = (list(collections),)
        else:
            cfb_filter_sql = "FALSE"
            cfb_params = ()

        sql = f"""
            SELECT
                fb.plugins_config       AS provider_plugins_config,
                fb.priority             AS provider_priority,
                fb.metadata             AS provider_metadata,
                fb.enabled              AS provider_enabled,

                c.collection_id         AS collection_id,
                c.plugins_config        AS collection_plugins_config
            FROM federation_backends fb
            LEFT JOIN (
                SELECT
                    cfb.collection_id,
                    cfb.plugins_config
                FROM collections_federation_backends cfb
                WHERE cfb.federation_backend_name = %s
                AND {cfb_filter_sql}
            ) AS c
            ON TRUE
            WHERE fb.name = %s
        """
        params = (name, *cfb_params, name)

        rows = self._execute(sql, params).fetchall()
        if not rows or not rows[0]["provider_plugins_config"]:
            raise KeyError(f"Provider '{name}' not found")

        base: dict[str, Any] = (
            (rows[0]["provider_plugins_config"] or {})
            | (rows[0]["provider_metadata"] or {})
            | {
                "priority": rows[0]["provider_priority"],
                "enabled": bool(rows[0]["provider_enabled"]),
                "name": name,
            }
        )
        base.setdefault("products", {})
        if isinstance(base.get("download"), dict):
            base["download"].setdefault("products", {})

        for r in rows:
            cid = r["collection_id"]
            if not cid:
                continue
            blob = r["collection_plugins_config"] or {}
            base["products"][cid] = blob.get("search", {}) or blob.get("api", {})
            if isinstance(base.get("download"), dict):
                base["download"]["products"][cid] = blob.get("download", {})

        return base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collection_to_json(collection: Any) -> dict[str, Any]:
    """Serialize a Collection (or dict) for JSONB storage.

    Drops the ``federation:backends`` key from the stored content as it is
    materialized in a dedicated ``text[]`` column.

    :param collection: A :class:`~eodag.api.collection.Collection` instance or
        a plain dict representing a STAC collection.

    :returns: Dict ready for insertion into the ``content`` JSONB column.
    """
    if isinstance(collection, Collection):
        data = collection.model_dump(mode="json")
        data["_id"] = collection._id
    else:
        data = dict(collection)
    data.pop("federation:backends", None)
    return data


def _collection_from_json(data: Any) -> dict[str, Any]:
    """Deserialize a stored JSONB collection back to a STAC-shaped dict.

    Remaps ``_id`` (internal id) back to ``id`` so that
    ``Collection(**data)`` reconstructs correctly.

    :param data: Raw data loaded from the JSONB ``content`` column.

    :returns: STAC-shaped collection dict with ``id`` restored.
    """
    if data is None:
        return {}
    data = dict(data)
    if "_id" in data:
        data["id"] = data.pop("_id")
    return data


def _register_json_adapters(con: psycopg.Connection[Any]) -> None:
    """Register per-connection JSON adapters.

    - Plain ``dict`` parameters are dumped as ``jsonb`` (no need to wrap them
      in ``Jsonb(...)`` at every call site).
    - JSON (de)serialization uses ``orjson`` for performance.

    :param con: The psycopg connection on which to register the adapters.
    """
    con.adapters.register_dumper(dict, JsonbDumper)
    set_json_dumps(orjson.dumps, context=con)
    set_json_loads(orjson.loads, context=con)


def _ensure_extensions(con: psycopg.Connection[Any]) -> None:
    """Ensure required PostgreSQL extensions are installed.

    Extensions ``postgis`` and ``unaccent`` are required by this backend.
    Logs a warning and continues if an extension cannot be created (e.g. because
    a superuser is required) rather than raising an error.

    :param con: The psycopg connection to use to install the extensions.
    """
    cur = con.cursor()
    for ext in ("postgis", "unaccent"):
        try:
            cur.execute(pg_sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(pg_sql.Identifier(ext)))
        except psycopg.Error:
            con.rollback()
            logger.warning(
                "Could not enable extension '%s'. It may need to be installed by a superuser.",
                ext,
            )


def create_collections_table(con: psycopg.Connection[Any]) -> None:
    """Create the ``collections`` table along with its indexes and triggers.

    The schema relies on:
    - PostgreSQL 12+ generated columns for ``id``, ``internal_id``, datetimes
      and the FTS ``tsvector``.
    - PostGIS ``geometry(Polygon, 4326)`` and a GiST index for spatial filters.
    - GIN indexes on ``federation_backends`` (text[]) and ``tsv`` (tsvector).
    - A BEFORE INSERT/UPDATE trigger (``collections_set_derived_cols``) maintains
      the ``geometry``, ``datetime``, ``end_datetime``, and ``tsv`` columns from
      the ``content`` JSONB (generated columns cannot reference JSONB expressions
      in all PostgreSQL versions, so a trigger is used instead).

    :param con: Open psycopg connection used to execute the DDL statements. The
        caller is responsible for committing.

    :raises: :class:`~psycopg.Error` if any DDL statement fails.
    """
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS collections (
            key BIGSERIAL PRIMARY KEY,
            content JSONB NOT NULL,
            id TEXT GENERATED ALWAYS AS (content->>'id') STORED UNIQUE,
            internal_id TEXT GENERATED ALWAYS AS (content->>'_id') STORED UNIQUE,
            datetime TIMESTAMPTZ,
            end_datetime TIMESTAMPTZ,
            geometry geometry(Polygon, 4326),
            federation_backends TEXT[],
            priority INTEGER,
            tsv tsvector
        );
        """
    )

    # Trigger to (re)compute derived columns (geometry, datetime, end_datetime, tsv)
    # from the JSON content on every INSERT or UPDATE.
    cur.execute(
        """
        CREATE OR REPLACE FUNCTION collections_set_derived_cols()
        RETURNS TRIGGER AS $$
        DECLARE
            bbox jsonb;
            xmin double precision;
            ymin double precision;
            xmax double precision;
            ymax double precision;
            kws text;
            dt_start text;
            dt_end text;
        BEGIN
            bbox := NEW.content #> '{extent,spatial,bbox,0}';
            IF bbox IS NULL OR jsonb_typeof(bbox) <> 'array' THEN
                NEW.geometry := NULL;
            ELSE
                xmin := (bbox->>0)::double precision;
                ymin := (bbox->>1)::double precision;
                xmax := (bbox->>2)::double precision;
                ymax := (bbox->>3)::double precision;
                NEW.geometry := ST_MakeEnvelope(xmin, ymin, xmax, ymax, 4326);
            END IF;

            dt_start := NEW.content #>> '{extent,temporal,interval,0,0}';
            NEW.datetime := CASE
                WHEN dt_start IS NULL THEN '-infinity'::timestamptz
                ELSE dt_start::timestamptz
            END;

            dt_end := NEW.content #>> '{extent,temporal,interval,0,1}';
            NEW.end_datetime := CASE
                WHEN dt_end IS NULL THEN 'infinity'::timestamptz
                ELSE dt_end::timestamptz
            END;

            SELECT string_agg(value, ' ')
            INTO kws
            FROM jsonb_array_elements_text(
                COALESCE(NEW.content->'keywords', '[]'::jsonb)
            ) AS value;

            NEW.tsv :=
                setweight(to_tsvector('simple',
                    coalesce(NEW.content->>'title', '')), 'A')
                || setweight(to_tsvector('simple',
                    coalesce(NEW.content->>'description', '')), 'B')
                || setweight(to_tsvector('simple',
                    coalesce(kws, '')), 'C');

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    cur.execute("DROP TRIGGER IF EXISTS collections_set_geometry_trg ON collections;")
    cur.execute("DROP TRIGGER IF EXISTS collections_set_derived_cols_trg ON collections;")
    cur.execute(
        """
        CREATE TRIGGER collections_set_derived_cols_trg
        BEFORE INSERT OR UPDATE OF content ON collections
        FOR EACH ROW EXECUTE FUNCTION collections_set_derived_cols();
        """
    )

    # Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_collections_datetime ON collections (datetime);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_collections_end_datetime ON collections (end_datetime);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_collections_geometry ON collections USING GIST (geometry);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_collections_fbs ON collections USING GIN (federation_backends);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_collections_tsv ON collections USING GIN (tsv);")


def create_federation_backends_table(con: psycopg.Connection[Any]) -> None:
    """Create the ``federation_backends`` table.

    :param con: Open psycopg connection used to execute the DDL statement. The
        caller is responsible for committing.

    :raises: :class:`~psycopg.Error` if the DDL statement fails.
    """
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS federation_backends (
            key BIGSERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            plugins_config JSONB NOT NULL,
            priority INTEGER NOT NULL,
            metadata JSONB,
            enabled BOOLEAN NOT NULL
        );
        """
    )


def create_collections_federation_backends_table(con: psycopg.Connection[Any]) -> None:
    """Create the per-collection federation backend configuration table.

    :param con: Open psycopg connection used to execute the DDL statements. The
        caller is responsible for committing.

    :raises: :class:`~psycopg.Error` if any DDL statement fails.
    """
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS collections_federation_backends (
            collection_id TEXT,
            federation_backend_name TEXT,
            plugins_config JSONB NOT NULL,
            PRIMARY KEY (collection_id, federation_backend_name)
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cfb_backend_collection
        ON collections_federation_backends (federation_backend_name, collection_id);
        """
    )
