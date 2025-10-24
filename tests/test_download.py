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
"""Download tests."""

import os

from eodag import SearchResult
from eodag.api.product import EOProduct
from eodag.config import PluginConfig
from eodag.plugins.authentication.aws_auth import AwsAuth
from eodag.plugins.download.aws import AwsDownload
from eodag.plugins.download.http import HTTPDownload

from stac_fastapi.eodag.config import get_settings


async def test_download_item_from_collection_stream(
    request_valid_raw, defaults, mock_base_stream_download_dict, mock_base_authenticate, stream_response
):
    """Download through eodag server catalog should return a valid response"""
    mock_base_stream_download_dict.return_value = stream_response

    resp = await request_valid_raw(f"data/peps/{defaults.product_type}/foo/downloadLink")
    assert resp.content == b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert resp.headers["content-disposition"] == 'attachment; filename="alphabet.txt"'
    assert resp.headers["content-type"] == "text/plain"


async def test_download_item_from_collection_no_stream(
    request_valid_raw, defaults, mock_download, mock_base_stream_download_dict, mock_base_authenticate, tmp_dir
):
    """Download through eodag server catalog should return a valid response even if streaming is not available"""
    # download should be performed locally then deleted if streaming is not available
    expected_file = tmp_dir / "foo.tar"
    expected_file.touch()
    mock_download.return_value = expected_file
    mock_base_stream_download_dict.side_effect = NotImplementedError()

    await request_valid_raw(f"data/peps/{defaults.product_type}/foo/downloadLink")
    mock_download.assert_called_once()
    # downloaded file should have been immediatly deleted from the server
    assert not os.path.exists(expected_file), f"File {expected_file} should have been deleted"


async def test_download_auto_order_whitelist(
    request_valid_raw,
    mock_base_authenticate,
    mock_order,
    mock_search,
    defaults,
    mock_http_base_stream_download_dict,
    stream_response,
):
    """Test that the order method is called when downloading a product
    from a federation backend included in the auto_order_whitelist.

    This test simulates downloading a product from a federated backend ('peps')
    and checks that the order function is triggered when the backend is present
    in the auto_order_whitelist configuration.
    """
    federation_backend = "peps"
    # update the auto_order_whitelist setting to include "peps"
    auto_order_whitelist = get_settings().auto_order_whitelist
    get_settings().auto_order_whitelist = [federation_backend]

    collection_id = defaults.product_type

    url = f"data/{federation_backend}/{defaults.product_type}/dummy_id/downloadLink"

    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product.product_type = collection_id
    config = PluginConfig()
    config.priority = 0
    downloader = HTTPDownload(federation_backend, config)

    product.register_downloader(downloader=downloader, authenticator=None)

    mock_search.return_value = SearchResult([product])
    mock_http_base_stream_download_dict.return_value = stream_response

    await request_valid_raw(url, search_result=SearchResult([product]))

    assert mock_order.called

    # restore the original auto_order_whitelist setting
    get_settings().auto_order_whitelist = auto_order_whitelist


async def test_download_redirect_response(request_valid_raw, mock_search, mock_presign_url, mock_aws_authenticate):
    """test that a reponse with status code 302 is returned if presigned urls are used"""
    product_type = "MO_GLOBAL_ANALYSISFORECAST_PHY_001_024"
    product = EOProduct(
        "cop_marine",
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy",
        ),
        productType=product_type,
    )
    product.assets.update({"a1": {"href": "https://s3.waw3-1.cloudferro.com/b1/a1/a1.json"}})
    product.assets.update({"a2": {"href": "https://s3.waw3-1.cloudferro.com/b1/a2/a2.json"}})

    config = PluginConfig()
    config.priority = 0
    downloader = AwsDownload("cop_marine", config)
    download_auth = AwsAuth("cop_marine", config)
    product.register_downloader(downloader=downloader, authenticator=download_auth)
    mock_search.return_value = SearchResult([product])

    mock_presign_url.return_value = "s3://s3.abc.com/a1/b1?AWSAccesskeyId=123&expires=1543649"

    await request_valid_raw(
        f"data/cop_marine/{product_type}/foo/a1",
        search_result=SearchResult([product]),
        expected_status_code=302,
        follow_redirects=False,
    )
