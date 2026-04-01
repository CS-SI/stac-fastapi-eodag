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

import json
from unittest import mock

from eodag import SearchResult
from eodag.api.product import EOProduct
from eodag.config import PluginConfig
from eodag.plugins.download.http import HTTPDownload

from stac_fastapi.eodag.app import stac_metadata_model
from stac_fastapi.eodag.extensions.data_download import BaseDataDownloadClient
from stac_fastapi.eodag.models.item import create_stac_item


def test_get_data_with_file_delegates_to_get_data(mock_base_data_download_get_data):
    """get_data_with_file must delegate to get_data with the provided file path."""
    client = BaseDataDownloadClient()
    request = mock.Mock()
    expected_response = object()
    mock_base_data_download_get_data.return_value = expected_response

    response = client.get_data_with_file(
        "desp_cache",
        "collection",
        "item",
        "example.zarr",
        request,
        "group/foo.txt",
    )

    assert response is expected_response
    mock_base_data_download_get_data.assert_called_once_with(
        "desp_cache",
        "collection",
        "item",
        "example.zarr",
        request,
        "group/foo.txt",
    )


def test_items_response_includes_zarr_index_asset(defaults, mock_search_result, mock_item_get_settings):
    """create_stac_item should include a Zarr index asset when a Zarr asset is present."""
    search_result = mock_search_result
    product = search_result[0]
    product.assets.update({"example.zarr": {"href": "https://data/peps/example.zarr"}})
    request = mock.Mock()
    request.app.state.dag.collections_config = {}
    mock_item_get_settings.return_value = mock.Mock(
        download_base_url="http://testserver/",
        auto_order_whitelist=[],
        keep_origin_url=False,
        origin_url_blacklist=[],
    )
    response = create_stac_item(
        product,
        stac_metadata_model,
        lambda extension_name: extension_name == "DataDownload",
        request,
        extension_names=[],
    )

    item = response
    assert "example.zarr" in item["assets"]
    assert "download_link" not in item["assets"]
    assert (
        item["assets"]["example.zarr"]["href"]
        == f"http://testserver/data/peps/{item['collection']}/{item['id']}/example.zarr"
    )
    assert "Zarr index" in item["assets"]
    assert (
        item["assets"]["Zarr index"]["href"]
        == f"http://testserver/data/peps/{item['collection']}/{item['id']}/zarr/index"
    )


async def test_zarr_index_listing(
    defaults,
    mock_list_zarr_files_from_metadata,
):
    """get_data should return the streamed file index for a .zarr asset."""
    collection = defaults.collection
    item_id = "dummy_id"
    client = BaseDataDownloadClient()
    product = EOProduct(
        "peps",
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id=item_id,
        ),
        collection=collection,
    )
    product.assets.update({"example.zarr": {"href": "https://data/peps/example.zarr"}})
    config = PluginConfig()
    config.priority = 0
    downloader = HTTPDownload("peps", config)
    product.register_downloader(downloader=downloader, authenticator=None)

    dag = mock.Mock()
    dag.search.return_value = SearchResult([product])
    request = mock.Mock()
    request.app.state.dag = dag
    request.base_url._url = "http://testserver/"
    mock_list_zarr_files_from_metadata.return_value = [
        {"path": ".zmetadata", "size": None, "url": f"/data/peps/{collection}/{item_id}/example.zarr/.zmetadata"},
        {"path": "group/foo.txt", "size": None, "url": f"/data/peps/{collection}/{item_id}/example.zarr/group/foo.txt"},
    ]

    response = client.get_data(
        "peps",
        collection,
        item_id,
        "example.zarr",
        request,
        "index",
    )
    res = json.loads(response.body)

    assert res["type"] == "stream-file-index"
    assert res["item_id"] == item_id
    assert res["collection_id"] == collection
    assert res["backend"] == "peps"
    assert res["file_count"] == 2
    assert [f["path"] for f in res["files"]] == [".zmetadata", "group/foo.txt"]
    assert res["files"][1]["url"] == f"/data/peps/{collection}/{item_id}/example.zarr/group/foo.txt"
    mock_list_zarr_files_from_metadata.assert_called_once_with(
        "https://data/peps/example.zarr",
        None,
    )


async def test_zarr_file_display(
    defaults,
    mock_data_download_requests_get,
):
    """get_data_with_file should request streaming for a file inside a .zarr asset."""
    collection = defaults.collection
    item_id = "dummy_id"
    client = BaseDataDownloadClient()
    product = EOProduct(
        "peps",
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id=item_id,
        ),
        collection=collection,
    )
    product.assets.update({"example.zarr": {"href": "https://data/peps/example.zarr"}})
    config = PluginConfig()
    config.priority = 0
    downloader = HTTPDownload("peps", config)
    product.register_downloader(downloader=downloader, authenticator=None)

    dag = mock.Mock()
    dag.search.return_value = SearchResult([product])
    request = mock.Mock()
    request.app.state.dag = dag
    request.base_url._url = "http://testserver/"
    mock_data_download_requests_get.return_value = mock.Mock(
        status_code=200,
        headers={"Content-Type": "text/plain"},
    )
    mock_data_download_requests_get.return_value.iter_content.return_value = iter([b"hello"])

    response = client.get_data_with_file(
        "peps",
        collection,
        item_id,
        "example.zarr",
        request,
        "group/foo.txt",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    mock_data_download_requests_get.assert_called_once_with(
        "https://data/peps/example.zarr/group/foo.txt",
        auth=None,
        stream=True,
    )
