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
"""Order tests."""

import logging

import pytest
import responses
from eodag import SearchResult, config
from eodag.api.product import EOProduct
from eodag.api.product.metadata_mapping import OFFLINE_STATUS, STAGING_STATUS
from eodag.config import load_default_config
from eodag.plugins.download.base import Download
from eodag.plugins.manager import PluginManager
from eodag.utils.exceptions import ValidationError

from stac_fastapi.eodag.config import get_settings


@pytest.mark.parametrize("post_data", [{"foo": "bar"}, {}])
async def test_order_ok(request_valid, post_data):
    """Order a product through eodag server and check if it has been ordered and polled correctly and contains assets"""
    federation_backend = "cop_ads"
    collection_id = "CAMS_EAC4"
    url = f"collections/{collection_id}/order"
    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product.collection = collection_id

    product_dataset = "cams-global-reanalysis-eac4"
    endpoint = "https://ads.atmosphere.copernicus.eu/api/retrieve/v1"
    product.properties["eodag:order_link"] = (
        f"{endpoint}/processes/{product_dataset}/execution" + '?{"request": {"quux": "abc"}}'
    )

    # order an offline product
    product.properties["order:status"] = OFFLINE_STATUS

    # add auth and download plugins to make the order works
    plugins_manager = PluginManager(load_default_config())
    download_plugin = plugins_manager.get_download_plugin(product)
    auth_plugin = plugins_manager.get_auth_plugin(download_plugin, product)
    auth_plugin.config.credentials = {"apikey": "anicekey"}
    product.register_downloader(download_plugin, auth_plugin)

    product_id = product.properties["id"]

    @responses.activate(registry=responses.registries.OrderedRegistry)
    async def run():
        responses.add(
            responses.POST,
            f"{endpoint}/processes/{product_dataset}/execution",
            status=200,
            content_type="application/json",
            body=f'{{"status": "accepted", "jobID": "{product_id}"}}'.encode("utf-8"),
            auto_calculate_content_length=True,
        )
        responses.add(
            responses.GET,
            f"{endpoint}/jobs/{product_id}",
            status=200,
            content_type="application/json",
            body=f'{{"status": "successful", "jobID": "{product_id}"}}'.encode("utf-8"),
            auto_calculate_content_length=True,
        )
        responses.add(
            responses.GET,
            f"{endpoint}/jobs/{product_id}/results",
            status=200,
            content_type="application/json",
            body=(f'{{"asset": {{"value": {{"href": "http://somewhere/download/{product_id}"}} }} }}'.encode("utf-8")),
            auto_calculate_content_length=True,
        )

        response = await request_valid(
            url=url,
            method="POST",
            post_data=post_data,
            search_result=SearchResult([product]),
            expected_search_kwargs=dict(
                collection=collection_id,
                provider=None,
                **{f"ecmwf:{k}": v for k, v in post_data.items()},
                validate=True,
            ),
        )

        # check that the id of the stac item is the one of the EOProduct,
        # which had taken the value of the order id (given in response "jobID" value)
        assert response["id"] == product.properties["eodag:order_id"] == product_id
        # check the links
        for link in response["links"]:
            assert link["rel"] in ["self", "collection"]
        # check that status has been correctly updated
        assert response["properties"]["order:status"] == "succeeded"
        # chech that the assets are available
        assert (
            response["assets"]["downloadLink"]["href"]
            == f"http://testserver/data/cop_ads/CAMS_EAC4/{product_id}/downloadLink"
        )

    await run()


@pytest.mark.parametrize("post_data", [{"foo": "bar"}, {}])
async def test_order_with_poll_pending(request_valid, post_data):
    """Order a product through eodag server with a pending poll and check"
    if it has been ordered correctly and its status is on staging"""
    federation_backend = "cop_ads"
    collection_id = "CAMS_EAC4"
    url = f"collections/{collection_id}/order"
    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product.collection = collection_id

    product_dataset = "cams-global-reanalysis-eac4"
    endpoint = "https://ads.atmosphere.copernicus.eu/api/retrieve/v1"
    product.properties["eodag:order_link"] = (
        f"{endpoint}/processes/{product_dataset}/execution" + '?{"inputs": {"qux": "quux"}}'
    )

    # order an offline product
    product.properties["order:status"] = OFFLINE_STATUS

    # add auth and download plugins to make the order works
    plugins_manager = PluginManager(load_default_config())
    download_plugin = plugins_manager.get_download_plugin(product)
    auth_plugin = plugins_manager.get_auth_plugin(download_plugin, product)
    auth_plugin.config.credentials = {"apikey": "anicekey"}
    product.register_downloader(download_plugin, auth_plugin)

    product_id = product.properties["id"]

    @responses.activate(registry=responses.registries.OrderedRegistry)
    async def run():
        responses.add(
            responses.POST,
            f"{endpoint}/processes/{product_dataset}/execution",
            status=200,
            content_type="application/json",
            body=f'{{"status": "accepted", "jobID": "{product_id}"}}'.encode("utf-8"),
            auto_calculate_content_length=True,
        )
        responses.add(
            responses.GET,
            f"{endpoint}/jobs/{product_id}",
            status=200,
            content_type="application/json",
            body=f'{{"status": "running", "jobID": "{product_id}"}}'.encode("utf-8"),
            auto_calculate_content_length=True,
        )
        responses.add(
            responses.GET,
            f"{endpoint}/jobs/{product_id}/results",
            status=200,
            content_type="application/json",
            body=(f'{{"asset": {{"value": {{"href": "http://somewhere/download/{product_id}"}} }} }}'.encode("utf-8")),
            auto_calculate_content_length=True,
        )

        response = await request_valid(
            url=url,
            method="POST",
            post_data=post_data,
            search_result=SearchResult([product]),
            expected_search_kwargs=dict(
                collection=collection_id,
                provider=None,
                **{f"ecmwf:{k}": v for k, v in post_data.items()},
                validate=True,
            ),
        )

        # check that the id of the stac item is the one of the EOProduct,
        # which had taken the value of the order id (given in response "jobID" value)
        assert response["id"] == product.properties["eodag:order_id"] == product_id
        # check the links
        for link in response["links"]:
            assert link["rel"] in ["self", "collection"]
        # check that status has been correctly updated
        assert response["properties"]["order:status"] == "ordered"
        # check that there is no asset available
        assert len(response["assets"]) == 0

    await run()


async def test_order_product_not_orderable_ko(request_not_found, mock_search):
    """Order a product through eodag server with a product which is not orderable must raise a NotFoundError"""
    federation_backend = "cop_ads"
    collection_id = "CAMS_EAC4"
    url = f"collections/{collection_id}/order"
    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product.collection = collection_id

    # try to order a product which is offline but which does not have an order link
    product.properties["order:status"] = OFFLINE_STATUS
    assert product.properties.get("eodag:order_link") is None

    mock_search.return_value = SearchResult([product])

    await request_not_found(
        url=url,
        method="POST",
        post_data={},
        error_message="Product is not orderable. Please download it directly.",
    )

    # try to order a product which has an order link but which is not offline
    product.properties["eodag:order_link"] = "https://ads.atmosphere.copernicus.eu/api/retrieve/v1"
    product.properties["order:status"] = STAGING_STATUS

    mock_search.return_value = SearchResult([product])

    await request_not_found(
        url=url,
        method="POST",
        post_data={},
        error_message="Product is not orderable. Please download it directly.",
    )


async def test_order_product_wrong_downloader_ko(request_not_found, mock_search, caplog):
    """Order a product through eodag server with a product which have a wrong downloader must raise a NotFoundError"""
    federation_backend = "cop_ads"
    collection_id = "CAMS_EAC4"
    url = f"collections/{collection_id}/order"
    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product.collection = collection_id

    product_dataset = "cams-global-reanalysis-eac4"
    endpoint = "https://ads.atmosphere.copernicus.eu/api/retrieve/v1"
    product.properties["eodag:order_link"] = f"{endpoint}/processes/{product_dataset}/execution" + '?{"qux": "quux"}'

    # try to order a product which is offline but which does not have a downloader
    product.properties["order:status"] = OFFLINE_STATUS
    assert product.downloader is None

    mock_search.return_value = SearchResult([product])

    with caplog.at_level(logging.ERROR):
        await request_not_found(
            url=url,
            method="POST",
            post_data={},
            error_message="Download order failed.",
        )
    assert "No downloader available" in caplog.messages[0]

    # try to order a product which has a downloader but without order() method
    dl_config = config.PluginConfig.from_mapping({"priority": 1, "type": "HTTPDownload"})
    product.downloader = Download(federation_backend, dl_config)
    assert not hasattr(product.downloader, "order")

    mock_search.return_value = SearchResult([product])

    with caplog.at_level(logging.ERROR):
        await request_not_found(
            url=url,
            method="POST",
            post_data={},
            error_message="Download order failed.",
        )
    assert "No order() method available" in caplog.messages[1]


async def test_order_not_order_id_ko(request_not_found, mock_search, mock_order):
    """Order a product through eodag server and check if it has been ordered and polled correctly and contains assets"""
    federation_backend = "cop_ads"
    collection_id = "CAMS_EAC4"
    url = f"collections/{collection_id}/order"
    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product.collection = collection_id

    product_dataset = "cams-global-reanalysis-eac4"
    endpoint = "https://ads.atmosphere.copernicus.eu/api/retrieve/v1"
    product.properties["eodag:order_link"] = f"{endpoint}/processes/{product_dataset}/execution" + '?{"qux": "quux"}'

    # mock orderStatusLink and searchLink values to make order works without order id
    product.properties["eodag:status_link"] = f"{endpoint}/jobs/dummy_request_id"
    product.properties["eodag:search_link"] = f"{endpoint}/jobs/dummy_request_id/results"

    # try to order a product which is offline but which does not have an order id
    # this order id will not be mapped with the mock of the order
    product.properties["order:status"] = OFFLINE_STATUS
    assert product.properties.get("eodag:order_id") is None

    mock_search.return_value = SearchResult([product])

    await request_not_found(
        url=url,
        method="POST",
        post_data={},
        error_message="Download order failed.",
    )


@pytest.mark.parametrize("validate", [True, False])
async def test_order_validate(request_valid, settings_cache_clear, validate):
    """Product order through eodag server must be validated according to settings"""
    get_settings().validate_request = validate
    post_data = {"foo": "bar"}
    federation_backend = "cop_ads"
    collection_id = "CAMS_EAC4"
    expected_search_kwargs = dict(
        collection=collection_id,
        provider=None,
        validate=validate,
        **{f"ecmwf:{k}": v for k, v in post_data.items()},
    )
    url = f"collections/{collection_id}/order"
    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product.collection = collection_id

    product_dataset = "cams-global-reanalysis-eac4"
    endpoint = "https://ads.atmosphere.copernicus.eu/api/retrieve/v1"
    product.properties["eodag:order_link"] = (
        f"{endpoint}/processes/{product_dataset}/execution" + '?{"inputs": {"qux": "quux"}}'
    )

    # order an offline product
    product.properties["order:status"] = OFFLINE_STATUS

    # add auth and download plugins to make the order works
    plugins_manager = PluginManager(load_default_config())
    download_plugin = plugins_manager.get_download_plugin(product)
    auth_plugin = plugins_manager.get_auth_plugin(download_plugin, product)
    auth_plugin.config.credentials = {"apikey": "anicekey"}
    product.register_downloader(download_plugin, auth_plugin)

    product_id = product.properties["id"]

    @responses.activate(registry=responses.registries.OrderedRegistry)
    async def run():
        responses.add(
            responses.POST,
            f"{endpoint}/processes/{product_dataset}/execution",
            status=200,
            content_type="application/json",
            body=f'{{"status": "accepted", "jobID": "{product_id}"}}'.encode("utf-8"),
            auto_calculate_content_length=True,
        )
        responses.add(
            responses.GET,
            f"{endpoint}/jobs/{product_id}",
            status=200,
            content_type="application/json",
            body=f'{{"status": "successful", "jobID": "{product_id}"}}'.encode("utf-8"),
            auto_calculate_content_length=True,
        )
        responses.add(
            responses.GET,
            f"{endpoint}/jobs/{product_id}/results",
            status=200,
            content_type="application/json",
            body=(f'{{"asset": {{"value": {{"href": "http://somewhere/download/{product_id}"}} }} }}'.encode("utf-8")),
            auto_calculate_content_length=True,
        )

        await request_valid(
            url=url,
            method="POST",
            post_data=post_data,
            search_result=SearchResult([product]),
            expected_search_kwargs=expected_search_kwargs,
        )

    await run()


async def test_order_validate_with_errors(app, app_client, mocker, settings_cache_clear):
    """Order a product through eodag server with invalid parameters must return informative error message"""
    get_settings().validate_request = True
    collection_id = "AG_ERA5"
    errors = [
        ("wekeo_ecmwf", ValidationError("2 error(s). ecmwf:version: Field required; ecmwf:variable: Field required")),
        ("cop_cds", ValidationError("2 error(s). ecmwf:version: Field required; ecmwf:variable: Field required")),
    ]
    expected_response = {
        "code": "400",
        "description": "Something went wrong",
        "errors": [
            {
                "provider": "wekeo_ecmwf",
                "error": "ValidationError",
                "status_code": 400,
                "message": "2 error(s). ecmwf:version: Field required; ecmwf:variable: Field required",
            },
            {
                "provider": "cop_cds",
                "error": "ValidationError",
                "status_code": 400,
                "message": "2 error(s). ecmwf:version: Field required; ecmwf:variable: Field required",
            },
        ],
    }

    mock_search = mocker.patch.object(app.state.dag, "search")
    mock_search.return_value = SearchResult([], 0, errors)

    response = await app_client.request(
        "POST",
        f"/collections/{collection_id}/order",
        json=None,
        follow_redirects=True,
        headers={},
    )
    response_content = response.json()

    assert response.status_code == 400
    assert "ticket" in response_content
    response_content.pop("ticket", None)
    assert expected_response == response_content


async def test_order_product_with_polytope_shape(app, app_client, mocker):
    """Order a product through eodag server with ECMWF Polytope shape must succeed"""
    federation_backend = "cop_ads"
    collection_id = "CAMS_EAC4"
    post_data: dict = {
        "feature": {
            "shape": [
                [50.0, 50.0],
                [50.0, 60.0],
                [60.0, 60.0],
                [60.0, 50.0],
                [50.0, 50.0],
            ],
            "type": "polygon",
        }
    }
    # prepare product
    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product_dataset = "cams-global-reanalysis-eac4"
    endpoint = "https://ads.atmosphere.copernicus.eu/api/retrieve/v1"
    product.properties["eodag:order_link"] = (
        f"{endpoint}/processes/{product_dataset}/execution" + '?{"inputs": {"qux": "quux"}}'
    )
    product.properties["order:status"] = OFFLINE_STATUS
    # add auth and download plugins to make the order works
    plugins_manager = PluginManager(load_default_config())
    download_plugin = plugins_manager.get_download_plugin(product)
    auth_plugin = plugins_manager.get_auth_plugin(download_plugin, product)
    auth_plugin.config.credentials = {"apikey": "anicekey"}
    product.register_downloader(download_plugin, auth_plugin)

    # the only part to check in this test are the arguments passed to search
    mock_order = mocker.patch.object(download_plugin, "order")
    product_id = product.properties["id"]

    def set_order_id(product, auth, timeout):
        product.properties["eodag:order_id"] = product_id

    mock_order.side_effect = set_order_id
    mock_search = mocker.patch.object(app.state.dag, "search")
    mock_search.return_value = SearchResult([product], 1)

    # order product
    await app_client.request(
        "POST",
        f"/collections/{collection_id}/order",
        json=post_data,
        follow_redirects=True,
        headers={},
    )
    geometry = mock_search.call_args[1]["geometry"]
    # converts the geometry back to a Shapely polygon
    shape = {
        "type": "polygon",
        "shape": [[y, x] for x, y in geometry.exterior.coords],
    }
    assert shape == post_data["feature"]


async def test_order_product_with_area(app, app_client, mocker):
    """Order a product through eodag server with bounding box in area format must succeed"""
    federation_backend = "cop_ads"
    collection_id = "CAMS_EAC4"
    post_data: dict = {"area": [64.0, 51.0, 52.0, 63.0]}
    expected_bbox = [51.0, 52.0, 63.0, 64.0]
    # prepare product
    product = EOProduct(
        federation_backend,
        dict(
            geometry="POINT (0 0)",
            title="dummy_product",
            id="dummy_id",
        ),
    )
    product_dataset = "cams-global-reanalysis-eac4"
    endpoint = "https://ads.atmosphere.copernicus.eu/api/retrieve/v1"
    product.properties["eodag:order_link"] = (
        f"{endpoint}/processes/{product_dataset}/execution" + '?{"inputs": {"qux": "quux"}}'
    )
    product.properties["order:status"] = OFFLINE_STATUS
    # add auth and download plugins to make the order works
    plugins_manager = PluginManager(load_default_config())
    download_plugin = plugins_manager.get_download_plugin(product)
    auth_plugin = plugins_manager.get_auth_plugin(download_plugin, product)
    auth_plugin.config.credentials = {"apikey": "anicekey"}
    product.register_downloader(download_plugin, auth_plugin)

    # the only part to check in this test are the arguments passed to search
    mock_order = mocker.patch.object(download_plugin, "order")
    product_id = product.properties["id"]

    def set_order_id(product, auth, timeout):
        product.properties["eodag:order_id"] = product_id

    mock_order.side_effect = set_order_id
    mock_search = mocker.patch.object(app.state.dag, "search")
    mock_search.return_value = SearchResult([product], 1)

    # order product
    await app_client.request(
        "POST",
        f"/collections/{collection_id}/order",
        json=post_data,
        follow_redirects=True,
        headers={},
    )
    bbox = mock_search.call_args[1]["bbox"]
    assert bbox == expected_bbox
