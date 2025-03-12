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


async def test_download_item_from_collection_stream(
    request_valid_raw, defaults, mock_base_stream_download_dict, mock_base_authenticate, stream_response
):
    """Download through eodag server catalog should return a valid response"""
    mock_base_stream_download_dict.return_value = stream_response

    resp = await request_valid_raw(f"data/peps/{defaults.product_type}/foo/downloadLink")
    assert resp.content == b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert resp.headers["content-disposition"] == "attachment; filename=alphabet.txt"
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
