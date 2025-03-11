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
"""Queryables tests."""

import os
from typing import Annotated, Literal

import geojson
from pydantic import Field

json_file_path = os.path.join(os.path.dirname(__file__), "resources/datetime.json")


async def test_basic_queryables(request_valid):
    """Response for /queryables request without filters must contain correct fields"""
    res = await request_valid("queryables", check_links=False)
    assert "properties" in res
    assert "collection" in res["properties"]
    assert len(res["properties"]) == 1
    assert "additionalProperties" in res and res["additionalProperties"]
    assert "description" in res and res["description"] == "Queryable names for the stac-fastapi."
    assert "title" in res and res["title"] == "Queryables for stac-fastapi."
    assert "type" in res and res["type"] == "object"


async def test_collection_queryables(mock_list_queryables, app_client):
    """Response for queryables of specific collection must contain values returned by eodag lib"""
    eodag_response = {
        "providerProductType": Annotated[
            Literal[tuple(sorted(["SAR", "GRD"]))], Field(default="SAR", **{"title": "Product type"})
        ],
        "start": Annotated[str, Field(..., **{"title": "Start date"})],
        "end": Annotated[str, Field(..., **{"title": "End date"})],
    }
    mock_list_queryables.return_value = eodag_response
    response = await app_client.request(
        method="GET",
        url="/collections/ABC_SAR/queryables",
        follow_redirects=True,
    )
    result = geojson.loads(response.content.decode("utf-8"))
    assert "properties" in result
    assert len(result["properties"]) == 2
    assert "product:type" in result["properties"]
    assert result["properties"]["product:type"]["default"] == "SAR"
    assert result["properties"]["product:type"]["enum"] == ["GRD", "SAR"]
    assert "datetime" in result["properties"]


async def test_ref_in_product_type_queryables(defaults, app_client):
    """The queryables should not have '$ref'."""
    response = await app_client.get(f"/collections/{defaults.product_type}/queryables", follow_redirects=True)
    resp_json = response.content.decode("utf-8")
    assert "$ref" not in resp_json, "there is a '$ref' in the /queryables response"
