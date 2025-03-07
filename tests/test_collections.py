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
"""Collections tests."""

import json


async def test_collection(request_valid, defaults):
    """Requesting a collection through eodag server should return a valid response"""
    result = await request_valid(f"collections/{defaults.product_type}")
    assert result["id"] == defaults.product_type
    for link in result["links"]:
        assert link["rel"] in ["self", "root", "items", "parent"]


async def test_list_collections(app_client, mock_list_product_types):
    """A simple request to list collections must succeed"""
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
    ]

    r = await app_client.get("/collections")
    assert mock_list_product_types.called
    assert r.status_code == 200
    assert ["S2_MSI_L1C", "S2_MSI_L2A"] == [
        col["id"] for col in json.loads(r.content.decode("utf-8")).get("collections", [])
    ]


async def test_search_collections_ok(app_client, mock_list_product_types, mock_guess_product_type):
    """A collections search must succeed"""
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
    ]
    mock_guess_product_type.return_value = ["S2_MSI_L1C"]

    r = await app_client.get("/collections?q=TERM1,TERM2")
    assert mock_list_product_types.called
    mock_guess_product_type.assert_called_once_with(free_text="TERM1,TERM2", missionStartDate=None, missionEndDate=None)
    assert r.status_code == 200
    assert ["S2_MSI_L1C"] == [col["id"] for col in json.loads(r.content.decode("utf-8")).get("collections", [])]


async def test_search_collections_nok(app_client, mock_list_product_types):
    """A collections search with a not supported filter must return all collections"""
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
    ]
    r = await app_client.get("/collections?gibberish=gibberish")
    assert mock_list_product_types.called
    assert r.status_code == 200
    assert ["S2_MSI_L1C", "S2_MSI_L2A"] == [
        col["id"] for col in json.loads(r.content.decode("utf-8")).get("collections", [])
    ]
