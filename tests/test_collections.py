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

from stac_fastapi.eodag.config import get_settings


async def test_collection(
    request_valid,
    defaults,
    mock_stac_discover_queryables,
    mock_token_authenticate,
    mock_oidc_refresh_token_base_init,
    mock_oidc_token_exchange_auth_authenticate,
):
    """Requesting a collection through eodag server should return a valid response"""
    result = await request_valid(f"collections/{defaults.product_type}")
    assert result["id"] == defaults.product_type
    assert all(isinstance(v, list) for v in result["summaries"].values())
    assert len(result["summaries"]["federation:backends"]) > 0
    for link in result["links"]:
        assert link["rel"] in ["self", "items", "http://www.opengis.net/def/rel/ogc/1.0/queryables"]


async def test_list_collections(app_client, mock_list_product_types):
    """A simple request to list collections must succeed"""
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
    ]

    r = await app_client.get("/collections")
    assert mock_list_product_types.called
    assert r.status_code == 200
    result = r.json()
    assert ["S2_MSI_L1C", "S2_MSI_L2A"] == [col["id"] for col in result.get("collections", [])]

    assert len(result["links"]) == 2
    assert result["links"][0] == {
        "rel": "self",
        "type": "application/json",
        "href": "http://testserver/collections",
        "title": "Collections",
    }
    assert result["links"][1] == {
        "rel": "root",
        "type": "application/json",
        "href": "http://testserver/",
        "title": get_settings().stac_fastapi_title,
    }


async def test_search_collections_freetext_ok(app_client, mock_list_product_types, mock_guess_product_type):
    """A collections free-text search must succeed"""
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
    ]
    mock_guess_product_type.return_value = ["S2_MSI_L1C"]

    r = await app_client.get("/collections?q=TERM1,TERM2")
    assert mock_list_product_types.called
    mock_guess_product_type.assert_called_once_with(free_text="TERM1,TERM2", missionStartDate=None, missionEndDate=None)
    assert r.status_code == 200
    assert ["S2_MSI_L1C"] == [col["id"] for col in r.json().get("collections", [])]


async def test_search_collections_freetext_nok(app_client, mock_list_product_types):
    """A collections free-text search with a not supported filter must return all collections"""
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
    ]
    r = await app_client.get("/collections?gibberish=gibberish")
    assert mock_list_product_types.called
    assert r.status_code == 200
    assert ["S2_MSI_L1C", "S2_MSI_L2A"] == [col["id"] for col in r.json().get("collections", [])]


async def test_search_collections_query(app_client, mock_list_product_types):
    """A collections query search must succeed"""
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
    ]
    r = await app_client.get('/collections?query={"federation:backends":{"eq":"peps"}}')

    mock_list_product_types.assert_called_once_with(provider="peps", fetch_providers=False)
    assert r.status_code == 200
    assert ["S2_MSI_L1C", "S2_MSI_L2A"] == [col["id"] for col in r.json().get("collections", [])]


async def test_search_collections_bbox(app_client, mock_list_product_types, mocker, app):
    """A collections bbox search must succeed"""
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
        {"_id": "S1_SAR_GRD", "ID": "S1_SAR_GRD"},
    ]
    mocker.patch.dict(
        app.state.ext_stac_collections,
        {
            "S2_MSI_L2A": {"extent": {"spatial": {"bbox": [[20, 20, 30, 30]]}}},
            "S1_SAR_GRD": {"extent": {"spatial": {"bbox": [[0, 0, 10, 10]]}}},
        },
    )
    r = await app_client.get("/collections?bbox=-5,0,0,5")

    assert r.status_code == 200
    assert ["S2_MSI_L1C", "S1_SAR_GRD"] == [col["id"] for col in r.json().get("collections", [])]
