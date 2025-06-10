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
        "rel": "root",
        "type": "application/json",
        "href": "http://testserver/",
        "title": get_settings().stac_fastapi_title,
    }
    assert result["links"][1] == {
        "rel": "self",
        "type": "application/json",
        "href": "http://testserver/collections",
        "title": "Current Page",
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
    mock_guess_product_type.assert_called_once_with(
        free_text=["TERM1", "TERM2"], missionStartDate=None, missionEndDate=None
    )
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


async def test_collections_pagination_default_and_custom_limits(app_client, mock_list_product_types):
    """
    Test pagination behavior for collections with default and custom limits.

    This test ensures that:
    - The default limit is applied when no limit parameter is provided.
    - Custom limits adjust the number of returned collections and pagination links.
    """

    collections = []
    for i in range(12):
        collections.append(
            {
                "_id": f"sample_collection_{i}",
                "ID": "sample_collection",
                "title": "Sample Collection",
            }
        )

    mock_list_product_types.return_value = collections

    # Default limit returns 10 collections and correct pagination links
    r = await app_client.get("/collections")
    assert r.status_code == 200
    assert r.json()["numberReturned"] == 10  # limit
    assert r.json()["numberMatched"] == len(collections)
    cols = r.json()["collections"]
    assert len(cols) == 10
    links = r.json()["links"]
    assert len(links) == 3
    assert {"next", "root", "self"} == {link["rel"] for link in links}

    # Custom limit parameter adjusts returned collections and changes pagination links
    r = await app_client.get("/collections", params={"limit": 12})
    assert r.status_code == 200
    assert r.json()["numberReturned"] == 12  # limit
    assert r.json()["numberMatched"] == len(collections)
    cols = r.json()["collections"]
    assert len(cols) == 12
    links = r.json()["links"]
    assert len(links) == 2
    assert {"root", "self"} == {link["rel"] for link in links}


async def test_collections_pagination_with_offset_and_limit(app_client, mock_list_product_types):
    """
      Test pagination behavior for collections with offset and limit parameters.

    This test ensures that:
    - Pagination works correctly with offset and limit combinations.
    - Links such as `next`, `previous`, and `first` are generated appropriately.
    """
    mock_list_product_types.return_value = [
        {"_id": "S2_MSI_L1C", "ID": "S2_MSI_L1C", "title": "SENTINEL2 Level-1C"},
        {"_id": "S2_MSI_L2A", "ID": "S2_MSI_L2A"},
    ]

    # Default pagination with only 2 collections
    r = await app_client.get("/collections")
    links = r.json()["links"]
    assert r.json()["numberReturned"] == 2
    assert r.json()["numberMatched"] == 2
    cols = r.json()["collections"]
    assert len(cols) == 2
    assert {"root", "self"} == {link["rel"] for link in links}

    # limit should be positive
    r = await app_client.get("/collections", params={"limit": 0})
    assert r.status_code == 400

    # limit=1, should have a `next` link
    r = await app_client.get(
        "/collections",
        params={"limit": 1},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 1
    assert cols[0]["id"] == "S2_MSI_L1C"
    assert len(links) == 3
    assert {"root", "self", "next"} == {link["rel"] for link in links}
    next_link = list(filter(lambda link: link["rel"] == "next", links))[0]
    assert next_link["href"].endswith("?limit=1&offset=1")

    # limit=2, there should not be a next and first link
    r = await app_client.get(
        "/collections",
        params={"limit": 2},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 2
    assert cols[0]["id"] == "S2_MSI_L1C"
    assert cols[1]["id"] == "S2_MSI_L2A"
    assert len(links) == 2
    assert {"root", "self"} == {link["rel"] for link in links}

    # limit=3, there should not be a next/previous/first link
    r = await app_client.get(
        "/collections",
        params={"limit": 3},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 2
    assert cols[0]["id"] == "S2_MSI_L1C"
    assert cols[1]["id"] == "S2_MSI_L2A"
    assert len(links) == 2
    assert {"root", "self"} == {link["rel"] for link in links}

    # offset=3, because there are 2 collections, we should not have `next` or `prev` or `fisrt` links
    r = await app_client.get(
        "/collections",
        params={"offset": 3},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 0
    assert len(links) == 4
    assert {"root", "self", "previous", "first"} == {link["rel"] for link in links}
    prev_link = list(filter(lambda link: link["rel"] == "previous", links))[0]
    assert prev_link["href"].endswith("offset=0&limit=10")
    first_link = list(filter(lambda link: link["rel"] == "first", links))[0]
    assert first_link["href"].endswith("offset=0&limit=10")

    # offset=3,limit=1
    r = await app_client.get(
        "/collections",
        params={"limit": 1, "offset": 3},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 0
    assert len(links) == 4
    assert {"root", "self", "previous", "first"} == {link["rel"] for link in links}
    prev_link = list(filter(lambda link: link["rel"] == "previous", links))[0]
    assert prev_link["href"].endswith("?limit=1&offset=2")
    first_link = list(filter(lambda link: link["rel"] == "first", links))[0]
    assert first_link["href"].endswith("?limit=1&offset=0")

    # limit=2, offset=3, there should not be a next link
    r = await app_client.get(
        "/collections",
        params={"limit": 2, "offset": 3},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 0
    assert len(links) == 4
    assert {"root", "self", "previous", "first"} == {link["rel"] for link in links}
    prev_link = list(filter(lambda link: link["rel"] == "previous", links))[0]
    assert prev_link["href"].endswith("?limit=2&offset=1")
    first_link = list(filter(lambda link: link["rel"] == "first", links))[0]
    assert first_link["href"].endswith("?limit=2&offset=0")

    # offset=1,limit=1 should have a `previous` and `first` link
    r = await app_client.get(
        "/collections",
        params={"offset": 1, "limit": 1},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 1
    assert cols[0]["id"] == "S2_MSI_L2A"
    assert len(links) == 4
    assert {"root", "self", "previous", "first"} == {link["rel"] for link in links}
    prev_link = list(filter(lambda link: link["rel"] == "previous", links))[0]
    assert "offset" in prev_link["href"]
    first_link = list(filter(lambda link: link["rel"] == "first", links))[0]
    assert first_link["href"].endswith("?offset=0&limit=1")

    # offset=0, should not have next/previous/first link
    r = await app_client.get(
        "/collections",
        params={"offset": 0},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 2
    assert len(links) == 2
    assert {"root", "self"} == {link["rel"] for link in links}

    # offset=0,limit=1 should have a `next` link
    r = await app_client.get(
        "/collections",
        params={"offset": 0, "limit": 1},
    )
    cols = r.json()["collections"]
    links = r.json()["links"]
    assert len(cols) == 1
    assert cols[0]["id"] == "S2_MSI_L1C"
    assert len(links) == 3
    assert {"root", "self", "next"} == {link["rel"] for link in links}
    next_link = list(filter(lambda link: link["rel"] == "next", links))[0]
    assert "offset" in next_link["href"]
