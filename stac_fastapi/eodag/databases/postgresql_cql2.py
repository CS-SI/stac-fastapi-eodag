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
"""CQL2 to PostgreSQL SQL translator for EODAG's PostgreSQL backend."""

from __future__ import annotations

import re
from typing import Any

import cql2
import orjson
from eodag.databases.base import (
    BASE_COLLECTION_TABLE_COLUMNS,
    extract_properties,
    validate_supported_ops,
)

# Properties that map to text columns / values; default for non-mapped properties.
# Numeric-like JSONB values are compared as text by default which still works for
# CQL2's range/equality semantics on STAC fields (most are strings).

# cql2 emits the Postgres-flavored ARRAY operator ``@@`` for ``a_overlaps``.
# In real Postgres this token is the FTS match operator, so we rewrite it to the
# array overlap operator ``&&``.
_RE_OVERLAP_ARRAY = re.compile(r"@@\s*ARRAY\[")

# cql2 emits ``strip_accents(...)`` for the CQL2 ``accenti`` operator. PostgreSQL
# provides the ``unaccent()`` function via the ``unaccent`` extension.
_RE_STRIP_ACCENTS = re.compile(r"\bstrip_accents\s*\(", re.IGNORECASE)

# Scalar normalisation for A_CONTAINS / A_CONTAINEDBY / A_OVERLAPS:
# ``col @> 'value'``, ``col <@ 'value'``, ``col @@ 'value'``
# → ``col @> ARRAY['value']`` / ``col <@ ARRAY['value']`` / ``col @@ ARRAY['value']``.
# Skips values starting with ``{`` (PG array literal) or ``[`` (JSON array literal).
_RE_CONTAINS_SCALAR = re.compile(r"(@>|<@|@@)\s*'([^{[][^']*?)'")

# Unified JSONB array-operator rewrite.
#
# cql2 extracts content properties via ``->>`` / ``#>>`` which return ``text``.
# PostgreSQL has no array or JSONB operators for ``text``, so we must switch to
# the jsonb-returning forms (``->`` / ``#>``) and adapt the RHS accordingly.
#
# Handled operators:
#   @>  (A_CONTAINS)    → jsonb @> jsonb
#   <@  (A_CONTAINEDBY) → jsonb <@ jsonb
#   &&  (A_OVERLAPS)    → EXISTS sub-select (no native jsonb && jsonb)
#
# Handles one or more values in the ARRAY[...] literal.
_RE_JSONB_ARRAY_OP = re.compile(
    r"\(content\s*(->>|#>>)\s*'([^']+)'\)\s*(@>|<@|&&|=)\s*(ARRAY\[[^\]]+\])",
    re.IGNORECASE,
)

# a_equals on physical text[] columns: ``col = ARRAY[...]``.
# PostgreSQL ``=`` is order-sensitive; rewrite to order-independent
# bidirectional containment so the semantics match CQL2 a_equals.
# Only applies to bare identifiers (not content->> extractions, which are
# handled by _RE_JSONB_ARRAY_OP above).
_RE_TEXT_ARRAY_EQUALS = re.compile(r"(\b(?:c\.)?\w+\b)\s*=\s*(ARRAY\[[^\]]+\])")


def _rewrite_jsonb_array_op(m: re.Match) -> str:  # type: ignore[type-arg]
    """Rewrite a JSONB text-extraction + array-operator expression.

    Switches the LHS from text-extraction (``->>``, ``#>>``) to jsonb-extraction
    (``->``, ``#>``) and converts the ``ARRAY[...]`` RHS to a JSONB array literal
    for ``@>`` and ``<@``.  For ``&&`` (A_OVERLAPS) there is no native
    ``jsonb && jsonb`` operator, so an ``EXISTS`` sub-select is generated instead.

    :param m: Regex match object from :data:`_RE_JSONB_ARRAY_OP`.

    :returns: Rewritten SQL fragment using jsonb-typed operators.
    """
    extract_op = m.group(1)  # '->>' or '#>>'
    key = m.group(2)
    op = m.group(3)
    # Build jsonb-extraction LHS (drop the trailing '>' to get '->' or '#>')
    if extract_op == "->>":
        lhs = f"(content->'{key}')"
    else:  # '#>>'
        lhs = f"(content #> '{key}')"
    # Parse all values from ARRAY['v1', 'v2', ...]
    items = re.findall(r"'([^']*)'", m.group(4))
    if op == "&&":
        # No jsonb && jsonb operator; expand to EXISTS overlap check.
        items_sql = ", ".join(f"'{i}'" for i in items)
        return f"EXISTS (SELECT 1 FROM jsonb_array_elements_text({lhs}) _e WHERE _e = ANY(ARRAY[{items_sql}]))"
    json_rhs = orjson.dumps(items).decode()
    if op == "=":
        # a_equals: order-independent — both directions of containment.
        return f"({lhs} @> '{json_rhs}'::jsonb AND {lhs} <@ '{json_rhs}'::jsonb)"
    return f"{lhs} {op} '{json_rhs}'::jsonb"


def _replace_properties(sql: str, properties: set[str]) -> str:
    """Rewrite property references in the SQL.

    Properties matching a physical column (see ``BASE_COLLECTION_TABLE_COLUMNS``)
    are passed through; all others are translated to ``content->>'prop'`` (text)
    JSONB extraction expressions.

    :param sql: Raw SQL string emitted by cql2 with quoted property names.
    :param properties: Set of property names extracted from the CQL2 expression.

    :returns: SQL string with all property references replaced by their
        column name or JSONB extraction expression.
    """
    result = sql
    for prop in sorted(properties, key=len, reverse=True):
        if value := BASE_COLLECTION_TABLE_COLUMNS.get(prop):
            prop_expr = value
            quoted = f'"{value}"'
        else:
            # For dotted property names (e.g. ``summaries.platform``) convert to a
            # JSONB path expression so PostgreSQL navigates the nested structure
            # rather than looking for a flat top-level key named
            # ``"summaries.platform"``.
            if "." in prop:
                path = ",".join(prop.split("."))
                prop_expr = f"(content #>> '{{{path}}}')"  # e.g. (content #>> '{summaries,platform}')
            else:
                # Use ``->>`` to extract the JSON value as text (compatible with
                # most CQL2 comparison operators which produce text-typed RHS
                # literals).
                prop_expr = f"(content->>'{prop}')"
            quoted = f'"{prop}"'

        if quoted in result:
            result = result.replace(quoted, prop_expr)
        else:
            result = re.sub(rf"\b{re.escape(prop)}\b", prop_expr, result)

    return result


def _postgres_compat(sql: str) -> str:
    """Apply PostgreSQL-specific rewrites to the SQL emitted by cql2.

    Most of cql2's SQL output is already valid PostgreSQL, but a couple of
    tokens need to be adjusted for native semantics:

    - ``@@ ARRAY[...]`` is rewritten to ``&& ARRAY[...]`` so it uses the
      Postgres array-overlap operator instead of the FTS match operator.
    - ``strip_accents(...)`` is rewritten to ``unaccent(...)`` (requires the
      ``unaccent`` extension to be installed in the database).
    - ``col @> 'scalar'`` / ``col <@ 'scalar'`` / ``col @@ 'scalar'`` are
      normalised to the ARRAY form.
    - ``(content->>'k') OP ARRAY[...]`` / ``(content #>> 'path') OP ARRAY[...]``
      are rewritten to use jsonb-returning extraction and a JSONB array literal
      (or an EXISTS sub-select for ``&&``; bidirectional containment for ``=``).
    - ``col = ARRAY[...]`` on physical ``text[]`` columns is rewritten to
      order-independent ``@> AND <@`` containment (CQL2 a_equals is unordered).

    :param sql: SQL string with property references already rewritten by
        :func:`~stac_fastapi.eodag.databases.postgresql_cql2._replace_properties`.

    :returns: PostgreSQL-compatible SQL string ready for use as a WHERE clause.
    """
    result = _RE_OVERLAP_ARRAY.sub("&& ARRAY[", sql)
    result = _RE_STRIP_ACCENTS.sub("unaccent(", result)
    result = _RE_CONTAINS_SCALAR.sub(r"\1 ARRAY['\2']", result)
    result = _RE_JSONB_ARRAY_OP.sub(_rewrite_jsonb_array_op, result)
    # a_equals on physical text[] columns: rewrite to order-independent containment.
    result = _RE_TEXT_ARRAY_EQUALS.sub(
        lambda m: f"({m.group(1)} @> {m.group(2)} AND {m.group(1)} <@ {m.group(2)})",
        result,
    )
    return result


def cql2_json_to_sql(cql2_json: dict[str, Any]) -> str:
    """Validate CQL2 JSON and return a PostgreSQL-compatible WHERE SQL fragment.

    :param cql2_json: CQL2 filter expression as a parsed JSON dict.

    :raises ValueError: if the expression uses unsupported CQL2 operators.

    :returns: PostgreSQL-compatible WHERE clause fragment (without the
        ``WHERE`` keyword).
    """

    validate_supported_ops(cql2_json)

    expr = cql2.parse_json(orjson.dumps(cql2_json).decode())
    raw_sql = expr.to_sql()

    properties: set[str] = set()
    extract_properties(cql2_json, properties)
    where_sql = _replace_properties(raw_sql, properties)
    where_sql = _postgres_compat(where_sql)

    return where_sql
