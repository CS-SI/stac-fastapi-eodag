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
"""Zarr tests."""

from eodag import SearchResult
from eodag.api.product import EOProduct
from eodag.config import PluginConfig
from eodag.plugins.download.http import HTTPDownload


async def test_items_response_includes_zarr_index_asset(request_valid, defaults, mock_search, mock_search_result):
    """Items response should include a Zarr index asset when zarr is present."""
    search_result = mock_search_result
    product = search_result[0]
    product.assets.update({"zarr": {"href": "https://data/internal_fdp/example.zarr"}})

    mock_search.return_value = search_result
    response = await request_valid(f"search?collections={defaults.collection}", search_result=search_result)

    item = response["features"][0]
    assert "zarr" in item["assets"]
    assert item["assets"]["zarr"]["href"] == f"http://testserver/data/peps/{item['collection']}/{item['id']}/zarr"
    assert "Zarr index" in item["assets"]
    assert (
        item["assets"]["Zarr index"]["href"]
        == f"http://testserver/data/peps/{item['collection']}/{item['id']}/zarr/index"
    )


async def test_zarr_index_listing(request_valid_raw, defaults, mock_search, mock_download, tmp_dir):
    """Zarr index should list all files in the store."""
    collection = defaults.collection
    item_id = "dummy_id"
    product = EOProduct(
        "peps",
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id=item_id,
        ),
        collection=collection,
    )
    product.assets.update({"zarr": {"href": "https://data/internal_fdp/example.zarr"}})
    config = PluginConfig()
    config.priority = 0
    downloader = HTTPDownload("peps", config)
    product.register_downloader(downloader=downloader, authenticator=None)

    store = tmp_dir / "store.zarr"
    (store / "group").mkdir(parents=True)
    (store / "group" / "foo.txt").write_text("hello", encoding="utf-8")
    (store / "root.txt").write_text("root", encoding="utf-8")

    mock_search.return_value = SearchResult([product])
    mock_download.return_value = str(store)

    response = await request_valid_raw(
        f"data/peps/{collection}/{item_id}/zarr/index",
        search_result=SearchResult([product]),
    )
    res = response.json()

    assert res["type"] == "zarr-file-index"
    assert res["item_id"] == item_id
    assert res["collection_id"] == collection
    assert res["backend"] == "peps"
    assert res["file_count"] == 2
    assert [f["path"] for f in res["files"]] == ["group/foo.txt", "root.txt"]
    assert res["files"][0]["url"] == f"/data/peps/{collection}/{item_id}/zarr/group/foo.txt"


async def test_zarr_file_download(request_valid_raw, defaults, mock_search, mock_download, tmp_dir):
    """Zarr file should be retrievable by path."""
    collection = defaults.collection
    item_id = "dummy_id"
    product = EOProduct(
        "peps",
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id=item_id,
        ),
        collection=collection,
    )
    product.assets.update({"zarr": {"href": "https://data/internal_fdp/example.zarr"}})
    config = PluginConfig()
    config.priority = 0
    downloader = HTTPDownload("peps", config)
    product.register_downloader(downloader=downloader, authenticator=None)

    store = tmp_dir / "store.zarr"
    (store / "group").mkdir(parents=True)
    (store / "group" / "foo.txt").write_text("hello", encoding="utf-8")

    mock_search.return_value = SearchResult([product])
    mock_download.return_value = str(store)

    response = await request_valid_raw(
        f"data/peps/{collection}/{item_id}/zarr/group/foo.txt",
        search_result=SearchResult([product]),
    )

    assert response.content == b"hello"
    assert response.headers["content-type"].startswith("text/plain")
