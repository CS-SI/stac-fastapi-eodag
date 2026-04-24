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
"""STAC q expression parser for PostgreSQL ``tsquery``.

Supported syntax (same as the SQLite/FTS5 variant):
- bare terms (implicit OR between adjacent terms, per STAC default)
- quoted phrases ("exact phrase") -> emitted as PostgreSQL phrase tsquery
- explicit AND / OR operators
- parentheses for grouping

``+`` and ``-`` prefix operators are not supported and will raise ``ValueError``.

The output is a string usable with ``to_tsquery('simple', $expr)``.
"""

from __future__ import annotations

import re
from typing import cast

_FTS_TOKEN_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"|\(|\)|\bAND\b|\bOR\b|[^\s()"]+',
    flags=re.IGNORECASE,
)

_UNSUPPORTED_PREFIX_RE = re.compile(r"^[+-]")

_PRECEDENCE = {"OR": 1, "AND": 2}
_SYNTAX = frozenset(_PRECEDENCE) | {"(", ")"}

# tsquery operator mapping
_OP_MAP = {"AND": "&", "OR": "|"}

# Lexeme split (whitespace and basic punctuation) for phrases.
_LEXEME_SPLIT_RE = re.compile(r"\W+", flags=re.UNICODE)


def _escape_lexeme(token: str) -> str:
    """Escape a single lexeme for tsquery by wrapping it in single quotes.

    Internal single quotes are doubled to avoid tsquery syntax errors.

    :param token: Raw lexeme string to escape.

    :returns: The lexeme wrapped in single quotes with internal quotes doubled.
    """
    return "'" + token.replace("'", "''") + "'"


def _term_to_tsquery(token: str) -> str:
    """Convert one parsed token (bare word or quoted phrase) to a tsquery fragment.

    Quoted phrases are split into individual lexemes joined with the PostgreSQL
    phrase operator ``<->``.

    :param token: A bare-word token or a double-quoted phrase token.

    :raises ValueError: if a quoted phrase contains no lexemes after splitting.

    :returns: A tsquery fragment string (lexeme or phrase expression).
    """
    if token.startswith('"') and token.endswith('"') and len(token) >= 2:
        # Quoted phrase: split into lexemes joined with the phrase operator <->.
        inner = token[1:-1].replace('\\"', '"')
        lexemes = [w for w in _LEXEME_SPLIT_RE.split(inner) if w]
        if not lexemes:
            raise ValueError("Empty phrase in q expression")
        if len(lexemes) == 1:
            return _escape_lexeme(lexemes[0])
        return "(" + " <-> ".join(_escape_lexeme(w) for w in lexemes) + ")"
    return _escape_lexeme(token)


def _normalize_tokens(q: str) -> list[str]:
    """Tokenize a STAC ``q`` expression and insert implicit OR operators.

    Rejects the ``+`` and ``-`` prefix operators. Adjacent operands have an
    implicit ``OR`` inserted between them, following the STAC default.

    :param q: Raw STAC ``q`` filter string.

    :raises ValueError: if a token starts with an unsupported ``+`` or ``-``
        prefix operator.

    :returns: List of tokens with implicit ``OR`` operators inserted.
    """
    raw = cast(list[str], _FTS_TOKEN_RE.findall(q.strip()))
    if not raw:
        return []

    out: list[str] = []
    for tok in raw:
        up = tok.upper()
        if up in _SYNTAX:
            out.append(up)
            continue

        if _UNSUPPORTED_PREFIX_RE.match(tok):
            msg = f"Unsupported operator '{tok[0]}' in q expression. Use AND / OR / parentheses instead."
            raise ValueError(msg)

        out.append(tok)

    # Insert implicit OR (default STAC behavior) between adjacent operands.
    with_or: list[str] = []
    for i, tok in enumerate(out):
        with_or.append(tok)
        if i < len(out) - 1:
            nxt = out[i + 1]
            left_is_end = tok not in _SYNTAX or tok == ")"
            right_is_start = nxt not in _SYNTAX or nxt == "("
            if left_is_end and right_is_start:
                with_or.append("OR")

    return with_or


def _to_postfix(tokens: list[str]) -> list[str]:
    """Convert infix tokens to postfix order using the shunting-yard algorithm.

    Handles left-associative ``AND`` (higher precedence) and ``OR`` operators
    and parentheses for grouping.

    :param tokens: List of normalised infix tokens (operators, operands,
        parentheses) as produced by :func:`_normalize_tokens`.

    :raises ValueError: if parentheses are unbalanced.

    :returns: List of tokens in postfix (reverse-Polish) order.
    """
    out: list[str] = []
    ops: list[str] = []

    for tok in tokens:
        if tok not in _SYNTAX:
            out.append(tok)
        elif tok == "(":
            ops.append(tok)
        elif tok == ")":
            while ops and ops[-1] != "(":
                out.append(ops.pop())
            if not ops:
                raise ValueError("Unbalanced parentheses")
            ops.pop()
        else:  # AND / OR
            while ops and ops[-1] != "(" and _PRECEDENCE.get(ops[-1], 0) >= _PRECEDENCE[tok]:
                out.append(ops.pop())
            ops.append(tok)

    while ops:
        if ops[-1] in {"(", ")"}:
            raise ValueError("Unbalanced parentheses")
        out.append(ops.pop())

    return out


def _postfix_to_tsquery(postfix: list[str]) -> str:
    """Build a ``tsquery`` expression string from a list of postfix tokens.

    :param postfix: List of postfix-ordered tokens as produced by
        :func:`_to_postfix`.

    :raises ValueError: if an operator is encountered with fewer than two
        operands on the stack, or if the stack does not contain exactly one
        result after processing.

    :returns: A complete ``tsquery`` expression string.
    """
    stack: list[str] = []

    for tok in postfix:
        if tok in _PRECEDENCE:
            if len(stack) < 2:
                raise ValueError(f"Missing operand for operator {tok}")
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(f"({lhs}) {_OP_MAP[tok]} ({rhs})")
        else:
            stack.append(_term_to_tsquery(tok))

    if len(stack) != 1:
        raise ValueError("Invalid expression")
    return stack[0]


def stac_q_to_tsquery(q: str) -> str:
    """Convert a STAC ``q`` expression to a PostgreSQL ``tsquery`` string.

    Output is intended for ``to_tsquery('simple', $expr)``.

    :param q: STAC ``q`` filter string. Supports bare terms, ``"quoted phrases"``,
        ``AND`` / ``OR`` operators and parentheses for grouping. Returns an
        empty string if ``q`` contains no tokens.

    :raises ValueError: if ``q`` contains unsupported prefix operators (``+``,
        ``-``), an unbalanced parenthesis, or an otherwise malformed expression.

    :returns: A ``tsquery``-compatible expression string, or ``""`` if ``q``
        contains no tokens.
    """
    tokens = _normalize_tokens(q)
    if not tokens:
        return ""
    postfix = _to_postfix(tokens)
    return _postfix_to_tsquery(postfix)
