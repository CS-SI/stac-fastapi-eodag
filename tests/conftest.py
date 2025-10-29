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
"""main conftest"""

import os
import unittest.mock
from dataclasses import dataclass, field
from pathlib import Path
from string import ascii_uppercase
from tempfile import TemporaryDirectory
from typing import Any, Iterator, Optional, Union
from urllib.parse import urljoin

import pytest
from eodag import EODataAccessGateway
from eodag.api.product.metadata_mapping import OFFLINE_STATUS, ONLINE_STATUS
from eodag.api.search_result import SearchResult
from eodag.config import PluginConfig
from eodag.plugins.authentication.aws_auth import AwsAuth
from eodag.plugins.authentication.base import Authentication
from eodag.plugins.authentication.openid_connect import OIDCRefreshTokenBase
from eodag.plugins.authentication.token import TokenAuth
from eodag.plugins.authentication.token_exchange import OIDCTokenExchangeAuth
from eodag.plugins.download.base import Download
from eodag.plugins.download.http import HTTPDownload
from eodag.plugins.search.qssearch import StacSearch
from eodag.utils import StreamResponse
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from stac_fastapi.eodag.app import api, stac_metadata_model
from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.dag import init_dag
from tests import TEST_RESOURCES_PATH


@pytest.fixture(autouse=True, scope="session")
def mock_user_dir(session_mocker):
    """Mock home and eodag conf directory to tmp dir."""
    tmp_home_dir = TemporaryDirectory()
    session_mocker.patch("os.path.expanduser", return_value=tmp_home_dir.name)
    yield
    tmp_home_dir.cleanup()


@pytest.fixture(autouse=True, scope="session")
def mock_os_environ(mock_user_dir, session_mocker):
    """Mock os.environ to empty env."""
    session_mocker.patch.dict(os.environ, {}, clear=True)


@pytest.fixture(autouse=True, scope="session")
def disable_collections_fetch(mock_os_environ):
    """Disable auto fetching product types from providers."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("EODAG_EXT_COLLECTIONS_CFG_FILE", "")
        yield


@pytest.fixture(autouse=True, scope="session")
async def fake_credentials(disable_collections_fetch):
    """load fake credentials to prevent providers needing auth for search to be pruned."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("EODAG_CFG_FILE", os.path.join(TEST_RESOURCES_PATH, "wrong_credentials_conf.yml"))
        yield


@pytest.fixture()
async def settings_cache_clear():
    """
    Asynchronous generator function to clear the settings cache before and after a test.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
async def stream_response():
    """
    Asynchronous generator function to provide a stream response
    """
    return StreamResponse(
        content=iter(ascii_uppercase),
        filename="alphabet.txt",
        headers={"content-type": "text/plain"},
    )


@pytest.fixture(scope="session")
def app() -> Iterator[FastAPI]:
    """
    Asynchronous generator that initializes and yields the FastAPI application,
    with `available_providers` mocked to return an empty list.
    """
    # Mock the `available_providers` method of EODataAccessGateway
    with unittest.mock.patch.object(EODataAccessGateway, "available_providers", return_value=["peps", "creodias"]):
        # Initialize the FastAPI app
        app = api.app
        init_dag(app)
        app.state.stac_metadata_model = stac_metadata_model

        # Yield the app for use in tests
        yield app


@pytest.fixture(scope="function")
async def app_client(app):
    """
    Asynchronous fixture to provide a test client for the given app.
    """
    base_url = "http://testserver"
    if app.state.router_prefix != "":
        base_url = urljoin(base_url, app.state.router_prefix)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=base_url) as c:
        yield c


@pytest.fixture(scope="function")
def mock_search_result():
    """Generate eodag_api.search mock results."""
    search_result = SearchResult.from_geojson(
        {
            "features": [
                {
                    "properties": {
                        "eo:snow_cover": None,
                        "gsd": None,
                        "end_datetime": "2018-02-16T00:12:14.035Z",
                        "keyword": [],
                        "product:type": "OCN",
                        "eodag:download_link": (
                            "https://peps.cnes.fr/resto/collections/S1/578f1768-e66e-5b86-9363-b19f8931cc7b/download"
                        ),
                        "eodag:provider": "peps",
                        "eodag:collection": "S1_SAR_OCN",
                        "platform": "S1A",
                        "eo:cloud_cover": 0,
                        "title": "S1A_WV_OCN__2SSV_20180215T235323_20180216T001213_020624_023501_0FD3",
                        "sat:absolute_orbit": 20624,
                        "instruments": ["SAR-C", "SAR"],
                        "abstract": None,
                        "eodag:search_intersection": {
                            "coordinates": [
                                [
                                    [89.590721, 2.614019],
                                    [89.771805, 2.575546],
                                    [89.809341, 2.756323],
                                    [89.628258, 2.794767],
                                    [89.590721, 2.614019],
                                ]
                            ],
                            "type": "Polygon",
                        },
                        "license": "other",
                        "start_datetime": "2018-02-15T23:53:22.871Z",
                        "constellation": None,
                        "eodag:sensor_type": None,
                        "processing:level": None,
                        "sat:orbit_state": None,
                        "sar:instrument_mode": None,
                        "quicklook": None,
                        "order:status": ONLINE_STATUS,
                        "peps:providerProperty": "foo",
                    },
                    "id": "578f1768-e66e-5b86-9363-b19f8931cc7b",
                    "type": "Feature",
                    "geometry": {
                        "coordinates": [
                            [
                                [89.590721, 2.614019],
                                [89.771805, 2.575546],
                                [89.809341, 2.756323],
                                [89.628258, 2.794767],
                                [89.590721, 2.614019],
                            ]
                        ],
                        "type": "Polygon",
                    },
                    "assets": {"asset1": {"title": "asset1", "href": "https://peps.cnes.fr"}},
                },
                {
                    "properties": {
                        "eo:snow_cover": None,
                        "gsd": None,
                        "end_datetime": "2018-02-17T00:12:14.035Z",
                        "keywords": [],
                        "product:type": "OCN",
                        "eodag:download_link": (
                            "https://peps.cnes.fr/resto/collections/S1/578f1768-e66e-5b86-9363-b19f8931cc7c/download"
                        ),
                        "eodag:provider": "peps",
                        "eodag:collection": "S1_SAR_OCN",
                        "platform": "S1A",
                        "eo:cloud_cover": 0,
                        "title": "S1A_WV_OCN__2SSV_20180216T235323_20180217T001213_020624_023501_0FD3",
                        "sat:absolute_orbit": 20624,
                        "instruments": ["SAR-C", "SAR"],
                        "abstract": None,
                        "eodag:search_intersection": {
                            "coordinates": [
                                [
                                    [89.590721, 2.614019],
                                    [89.771805, 2.575546],
                                    [89.809341, 2.756323],
                                    [89.628258, 2.794767],
                                    [89.590721, 2.614019],
                                ]
                            ],
                            "type": "Polygon",
                        },
                        "license": "other",
                        "start_datetime": "2018-02-16T23:53:22.871Z",
                        "eodag:sensor_type": None,
                        "processing:level": None,
                        "sat:orbit_state": None,
                        "sar:instrument_mode": None,
                        "quicklook": None,
                        "order:status": OFFLINE_STATUS,
                    },
                    "id": "578f1768-e66e-5b86-9363-b19f8931cc7c",
                    "type": "Feature",
                    "geometry": {
                        "coordinates": [
                            [
                                [89.590721, 2.614019],
                                [89.771805, 2.575546],
                                [89.809341, 2.756323],
                                [89.628258, 2.794767],
                                [89.590721, 2.614019],
                            ]
                        ],
                        "type": "Polygon",
                    },
                    "assets": {"asset1": {"title": "asset1", "href": "https://somewhere.fr"}},
                },
            ],
            "type": "FeatureCollection",
        }
    )
    config = PluginConfig()
    config.priority = 0
    for p in search_result:
        p.downloader = Download("peps", config)
        p.downloader_auth = Authentication("peps", config)
    search_result.number_matched = None
    return search_result


@pytest.fixture(scope="function")
def mock_search(mocker, app):
    """
    Mocks the `search` method of the `app.state.dag` object.
    """
    return mocker.patch.object(app.state.dag, "search")


@pytest.fixture(scope="function")
def mock_list_collections(mocker, app):
    """
    Mocks the `list_collections` method of the `app.state.dag` object.
    """
    return mocker.patch.object(app.state.dag, "list_collections")


@pytest.fixture(scope="function")
def mock_guess_collection(mocker, app):
    """
    Mocks the `guess_collection` method of the `app.state.dag` object.
    """
    return mocker.patch.object(app.state.dag, "guess_collection")


@pytest.fixture(scope="function")
def mock_list_queryables(mocker, app):
    """
    Mocks the `list_queryables` method of the `app.state.dag` object.
    """
    return mocker.patch.object(app.state.dag, "list_queryables")


@pytest.fixture(scope="function")
def mock_stac_discover_queryables(mocker):
    """
    Mocks the `discover_queryables` method of the `app.state.dag` object.
    """
    return mocker.patch.object(StacSearch, "discover_queryables")


@pytest.fixture(scope="function")
def mock_download(mocker, app):
    """
    Mocks the `download` method of the `app.state.dag` object.
    """
    return mocker.patch.object(app.state.dag, "download")


@pytest.fixture(scope="function")
def mock_base_stream_download_dict(mocker):
    """
    Mocks the `_stream_download_dict` method of the `Download` plugin.
    """
    return mocker.patch.object(Download, "_stream_download_dict")


@pytest.fixture(scope="function")
def mock_http_base_stream_download_dict(mocker):
    """
    Mocks the `_stream_download_dict` method of the `Download` plugin.
    """
    return mocker.patch.object(HTTPDownload, "_stream_download_dict")


@pytest.fixture(scope="function")
def mock_order(mocker):
    """
    Mocks the `order` method of the `HTTPDownload` download plugin.
    """
    return mocker.patch.object(HTTPDownload, "order")


@pytest.fixture(scope="function")
def mock_base_authenticate(mocker, app):
    """
    Mocks the `authenticate` method of the `Authentication` plugin.
    """
    return mocker.patch.object(Authentication, "authenticate")


@pytest.fixture(scope="function")
def mock_token_authenticate(mocker, app):
    """
    Mocks the `authenticate` method of the `TokenAuth` authentication plugin.
    """
    return mocker.patch.object(TokenAuth, "authenticate")


@pytest.fixture(scope="function")
def mock_oidc_refresh_token_base_init(mocker):
    """
    Mocks the `__init__` method of the `OIDCRefreshTokenBase` authentication plugin.
    """
    return mocker.patch.object(OIDCRefreshTokenBase, "__init__")


@pytest.fixture(scope="function")
def mock_oidc_token_exchange_auth_authenticate(mocker):
    """
    Mocks the `authenticate` method of the `OIDCTokenExchangeAuth` authentication plugin.
    """
    return mocker.patch.object(OIDCTokenExchangeAuth, "authenticate")


@pytest.fixture(scope="function")
def mock_aws_authenticate(mocker, app):
    """
    Mocks the `authenticate` method of the `AwsAuth` plugin.
    """
    return mocker.patch.object(AwsAuth, "authenticate")


@pytest.fixture(scope="function")
def tmp_dir():
    """
    Get random temporary directory `Path`.
    """
    tmpdir = TemporaryDirectory()
    yield Path(tmpdir.name)
    tmpdir.cleanup()


@pytest.fixture(scope="function")
def request_valid_raw(app_client, mock_search, mock_search_result):
    """Make a raw request to the API and check the response."""

    async def _request_valid_raw(
        url: str,
        expected_search_kwargs: Union[list[dict[str, Any]], dict[str, Any], None] = None,
        method: str = "GET",
        post_data: Optional[Any] = None,
        search_call_count: Optional[int] = None,
        search_result: Optional[SearchResult] = None,
        expected_status_code: int = 200,
        follow_redirects: bool = True,
    ):
        if search_result:
            mock_search.return_value = search_result
        else:
            mock_search.return_value = mock_search_result

        response = await app_client.request(
            method,
            url,
            json=post_data,
            follow_redirects=follow_redirects,
            headers={"Content-Type": "application/json"} if method == "POST" else {},
        )

        if search_call_count is not None:
            assert mock_search.call_count == search_call_count

        if expected_search_kwargs is not None and search_call_count is not None and search_call_count > 1:
            assert isinstance(
                expected_search_kwargs,
                list,
            ), "expected_search_kwargs must be a list if search_call_count > 1"

            for single_search_kwargs in expected_search_kwargs:
                mock_search.assert_any_call(**single_search_kwargs)
        elif expected_search_kwargs is not None:
            try:
                mock_search.assert_called_once_with(**expected_search_kwargs)
            except AssertionError as e:
                pytest.fail(f"Assertion failed: {e}\nAdditional context: {response.text}.")

        assert expected_status_code == response.status_code, (
            f"For {method}: {url}, body: {post_data}, got: {str(response)}"
        )
        return response

    yield _request_valid_raw
    mock_search.reset_mock()


@pytest.fixture(scope="function")
def assert_links_valid(app_client, request_valid_raw, request_not_valid):
    """Checks that element links are valid"""

    async def _assert_links_valid(element: Any):
        assert isinstance(element, dict)
        assert "links" in element, f"links not found in {str(element)}"
        assert isinstance(element["links"], list)
        links = element["links"]

        known_rel = [
            "self",
            "root",
            "next",
            "child",
            "items",
            "service-desc",
            "service-doc",
            "conformance",
            "search",
            "retrieve",
            "data",
            "collection",
            "http://www.opengis.net/def/rel/ogc/1.0/queryables",
        ]
        required_links_rel = ["self"]

        for link in links:
            # known relations
            assert link["rel"] in known_rel
            # must start with app base-url
            assert link["href"].startswith(str(app_client.base_url))
            # must have a title
            assert "title" in link

            if link["rel"] != "search" and not link["href"].endswith("/search"):
                # GET must be valid
                await request_valid_raw(link["href"])
                # TODO: support then test HEAD method
            else:
                # search fails with missing collection
                await request_not_valid(link["href"])

            if link["rel"] in required_links_rel:
                required_links_rel.remove(link["rel"])

        # required relations
        assert len(required_links_rel) == 0, f"missing {required_links_rel} relation(s) in {links}"

    return _assert_links_valid


@pytest.fixture(scope="function")
def request_valid(request_valid_raw, assert_links_valid) -> Any:
    """Make a request to the API and check the response."""

    async def _request_valid(
        url: str,
        expected_search_kwargs: Union[list[dict[str, Any]], dict[str, Any], None] = None,
        method: str = "GET",
        post_data: Optional[Any] = None,
        search_call_count: Optional[int] = None,
        check_links: bool = True,
        search_result: Optional[SearchResult] = None,
    ):
        response = await request_valid_raw(
            url,
            expected_search_kwargs=expected_search_kwargs,
            method=method,
            post_data=post_data,
            search_call_count=search_call_count,
            search_result=search_result,
        )

        # Assert response format is GeoJSON
        result = response.json()

        if check_links:
            await assert_links_valid(result)

        return result

    return _request_valid


@pytest.fixture(scope="function")
def request_not_valid(app_client):
    """
    Fixture to test invalid requests and assert a 400 status code.
    """

    async def _request_not_valid(url: str, method: str = "GET", post_data: Optional[Any] = None) -> None:
        response = await app_client.request(
            method,
            url,
            json=post_data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"} if method == "POST" else {},
        )
        response_content = response.json()

        assert 400 == response.status_code
        assert "description" in response_content

    return _request_not_valid


@pytest.fixture(scope="function")
def request_not_found(app_client):
    """
    Fixture to test if a request returns a 404 Not Found error.
    """

    async def _request_not_found(
        url: str, method: str = "GET", post_data: Optional[Any] = None, error_message: Optional[str] = None
    ) -> None:
        response = await app_client.request(
            method,
            url,
            json=post_data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"} if method == "POST" else {},
        )
        response_content = response.json()

        assert 404 == response.status_code
        assert "description" in response_content
        if error_message:
            assert error_message in response_content["description"]

    return _request_not_found


@pytest.fixture(scope="function")
def request_accepted(app_client):
    """
    Fixture to test if a request is accepted and returns the expected response.
    """

    async def _request_accepted(url: str):
        response = await app_client.get(url, follow_redirects=True)
        response_content = response.json()
        assert 202 == response.status_code
        assert "description" in response_content
        assert "location" in response_content
        return response_content

    return _request_accepted


@pytest.fixture(scope="function")
def mock_presign_url(mocker):
    """Fixture for the presign_url function"""
    return mocker.patch.object(AwsAuth, "presign_url")


@dataclass
class TestDefaults:
    """
    A class to hold default test values.
    """

    collection: str = "S2_MSI_L1C"
    bbox_wkt: str = "POLYGON ((0.0 43.0, 1.0 43.0, 1.0 44.0, 0.0 44.0, 0.0 43.0))"
    bbox_geojson: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "Polygon",
            "coordinates": [[[0, 43], [1, 43], [1, 44], [0, 44], [0, 43]]],
        }
    )
    bbox_csv: str = "0,43,1,44"
    bbox_list: list = field(default_factory=lambda: [0, 43, 1, 44])
    start: str = "2018-01-20T00:00:00Z"
    end: str = "2018-01-25T00:00:00Z"


@pytest.fixture(scope="module")
def defaults():
    """
    Create and return an instance of TestDefaults.
    """
    return TestDefaults()
