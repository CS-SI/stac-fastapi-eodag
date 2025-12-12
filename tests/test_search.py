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
"""Search tests."""

import pytest
from eodag import EOProduct, SearchResult
from eodag.api.product.metadata_mapping import ONLINE_STATUS
from eodag.utils import format_dict_items
from eodag.utils.exceptions import ValidationError

from stac_fastapi.eodag.config import get_settings
from stac_fastapi.eodag.constants import DEFAULT_ITEMS_PER_PAGE
from stac_fastapi.eodag.core import eodag_search_next_page


@pytest.mark.parametrize("bbox", [("1",), ("0,43,1",), ("0,,1",), ("a,43,1,44",)])
async def test_request_params_invalid(bbox, request_not_valid, defaults):
    """
    Test the invalid request parameters for the search endpoint.
    """
    await request_not_valid(f"search?collections={defaults.collection}&bbox={bbox}")


@pytest.mark.parametrize("input_bbox,expected_geom", [(None, None), ("bbox_csv", "bbox_wkt")])
async def test_request_params_valid(request_valid, defaults, input_bbox, expected_geom):
    """
    Test the valid request parameters for the search endpoint.
    """
    input_qs = f"&bbox={getattr(defaults, input_bbox)}" if input_bbox else ""
    expected_kwargs = {"geom": getattr(defaults, expected_geom)} if expected_geom else {}

    await request_valid(
        f"search?collections={defaults.collection}{input_qs}",
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            raise_errors=False,
            count=False,
            validate=True,
            **expected_kwargs,
        ),
    )


async def test_count_search(request_valid, defaults, mock_search, mock_search_result):
    """
    Test the count setting during a search.
    """
    count = get_settings().count
    qs = f"search?collections={defaults.collection}"

    assert count is False, "Default count setting should be False"
    response = await request_valid(
        qs,
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            raise_errors=False,
            count=False,  # Ensure count is set to False
            validate=True,
        ),
    )
    assert response["numberMatched"] is None

    # Reset search mock, set "number_matched" attribute of the search results mock for a counting search
    # and set count to True
    mock_search.reset_mock()
    search_result = mock_search_result
    search_result.number_matched = len(search_result)
    get_settings().count = True

    response = await request_valid(
        qs,
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            raise_errors=False,
            count=True,  # Ensure count is set to True
            validate=True,
        ),
    )
    assert response["numberMatched"] == 2

    # Reset count setting to default
    get_settings().count = count


async def test_items_response(request_valid, defaults):
    """Returned items properties must be mapped as expected"""
    resp_json = await request_valid(
        f"search?collections={defaults.collection}",
    )
    res = resp_json["features"]
    assert len(res) == 2
    first_props = res[0]["properties"]
    assert set(res[0].keys()) == {
        "type",
        "stac_version",
        "stac_extensions",
        "bbox",
        "collection",
        "links",
        "assets",
        "id",
        "geometry",
        "properties",
    }
    assert first_props["federation:backends"] == ["peps"]
    assert first_props["datetime"] == "2018-02-15T23:53:22.871000Z"
    assert first_props["start_datetime"] == "2018-02-15T23:53:22.871000Z"
    assert first_props["end_datetime"] == "2018-02-16T00:12:14.035000Z"
    assert first_props["license"] == "other"
    assert first_props["platform"] == "S1A"
    assert first_props["instruments"] == ["SAR-C", "SAR"]
    assert first_props["eo:cloud_cover"] == 0
    assert first_props["sat:absolute_orbit"] == 20624
    assert first_props["product:type"] == "OCN"
    assert first_props["order:status"] == "succeeded"
    assert "asset1" in res[0]["assets"]
    assert (
        res[0]["assets"]["asset1"]["href"]
        == f"http://testserver/data/peps/{res[0]['collection']}/{res[0]['id']}/asset1"
    )
    assert res[1]["properties"]["order:status"] == "orderable"
    assert "assets" in res[0]
    assert "asset1" in res[0]["assets"]
    assert (
        res[0]["assets"]["asset1"]["href"]
        == f"http://testserver/data/peps/{res[0]['collection']}/{res[0]['id']}/asset1"
    )
    expected_extensions = [
        "https://stac-extensions.github.io/sat/v1.0.0/schema.json",
        "https://stac-extensions.github.io/product/v0.1.0/schema.json",
        "https://api.openeo.org/extensions/federation/0.1.0",
        "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
        "https://stac-extensions.github.io/storage/v1.0.0/schema.json",
    ]
    for ext in expected_extensions:
        assert ext in res[0]["stac_extensions"]

    # check order status and storage tier properties of the "OFFLINE" item when peps is whitelisted
    auto_order_whitelist = get_settings().auto_order_whitelist
    get_settings().auto_order_whitelist = ["peps"]

    resp_json = await request_valid(
        f"search?collections={defaults.collection}",
    )
    res = resp_json["features"]
    assert res[1]["properties"]["order:status"] == "succeeded"

    # restore the original auto_order_whitelist setting
    get_settings().auto_order_whitelist = auto_order_whitelist


async def test_items_response_unexpected_types(request_valid, defaults, mock_search_result):
    """Item properties contain values in unexpected types for processing level and platform
    These values should be tranformed so that the validation passes
    """
    result_properties = mock_search_result.data[0].properties
    result_properties["processing:level"] = 2
    result_properties["platform"] = ["P1", "P2"]
    resp_json = await request_valid(f"search?collections={defaults.collection}", search_result=mock_search_result)
    res = resp_json["features"]
    assert len(res) == 2
    first_props = res[0]["properties"]
    assert first_props["processing:level"] == "L2"
    assert first_props["platform"] == "P1,P2"


async def test_assets_with_different_download_base_url(request_valid, defaults):
    """Domain for download links should be as configured in settings"""
    settings = get_settings()
    settings.download_base_url = "http://otherserver/"
    resp_json = await request_valid(
        f"search?collections={defaults.collection}",
    )
    res = resp_json["features"]
    assert len(res) == 2
    assert "assets" in res[0]
    assert "asset1" in res[0]["assets"]
    assert (
        res[0]["assets"]["asset1"]["href"]
        == f"http://otherserver/data/peps/{res[0]['collection']}/{res[0]['id']}/asset1"
    )


async def test_no_invalid_symbols_in_urls(request_valid, defaults, mock_search_result):
    """All urls (download urls, links) should be quoted so that there are no invalid symbols"""
    result_properties = mock_search_result.data[0].properties
    result_properties["id"] = "id,with,commas"
    result_assets = mock_search_result.data[0].assets
    result_assets["asset*star"] = {"title": "asset*star", "href": "https://somewhere.fr"}
    resp_json = await request_valid("search?collections=S1_SAR_OCN", search_result=mock_search_result)
    res = resp_json["features"]
    assert len(res) == 2
    assert "," not in res[0]["assets"]["downloadLink"]
    assert res[0]["links"][1]["href"] == "http://testserver/collections/S1_SAR_OCN/items/id%2Cwith%2Ccommas"
    asset = res[0]["assets"]["asset*star"]
    assert asset["href"].endswith("asset%2Astar")


async def test_not_found(request_not_found):
    """A request to eodag server with a not supported product type must return a 404 HTTP error code"""
    await request_not_found("search?collections=ZZZ&bbox=0,43,1,44")


async def test_search_results_with_errors(request_valid, mock_search_result, defaults):
    """Search through eodag server must not display provider's error if it's not empty result"""
    errors = [
        ("usgs", Exception("foo error")),
        ("aws_eos", Exception("boo error")),
    ]
    mock_search_result.errors.extend(errors)

    await request_valid(
        f"search?collections={defaults.collection}",
        search_result=mock_search_result,
    )


@pytest.mark.parametrize(
    ("input_start", "input_end", "expected_start", "expected_end"),
    [
        ("start", "end", "start", "end"),
        ("start", "..", "start", None),
        ("..", "end", None, "end"),
        ("start", None, "start", "start"),
        (None, None, None, None),
    ],
)
async def test_date_search(request_valid, defaults, input_start, input_end, expected_start, expected_end):
    """Search through eodag server /search endpoint using dates filering should return a valid response"""
    input_date_qs = f"&datetime={getattr(defaults, input_start, input_start)}" if input_start else ""
    input_date_qs += f"/{getattr(defaults, input_end, input_end)}" if input_end else ""

    expected_kwargs = {"start": getattr(defaults, expected_start)} if expected_start else {}
    expected_kwargs |= {"end": getattr(defaults, expected_end)} if expected_end else {}

    await request_valid(
        f"search?collections={defaults.collection}&bbox={defaults.bbox_csv}{input_date_qs}",
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            geom=defaults.bbox_wkt,
            raise_errors=False,
            count=False,
            validate=True,
            **expected_kwargs,
        ),
    )


@pytest.mark.parametrize("use_dates", [(False,), (True,)])
async def test_date_search_from_items(request_valid, defaults, use_dates):
    """Search through eodag server collection/items endpoint using dates filering should return a valid response"""
    input_date_qs = f"&datetime={defaults.start}/{defaults.end}" if use_dates else ""
    expected_kwargs = {"start": defaults.start, "end": defaults.end} if use_dates else {}

    await request_valid(
        f"collections/{defaults.collection}/items?bbox={defaults.bbox_csv}{input_date_qs}",
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            geom=defaults.bbox_wkt,
            raise_errors=False,
            count=False,
            validate=True,
            **expected_kwargs,
        ),
    )


async def test_filter_extension_items(request_valid, defaults, mock_search):
    """Search through eodag server /items endpoint using the filter extension should return a valid response"""

    # one parameter
    expected_kwargs = {"sat:absolute_orbit": 1234}
    await request_valid(
        f"collections/{defaults.collection}/items?bbox={defaults.bbox_csv}&filter=sat:absolute_orbit=1234",
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            geom=defaults.bbox_wkt,
            raise_errors=False,
            count=False,
            validate=True,
            **expected_kwargs,
        ),
    )
    mock_search.reset_mock()

    # two parameters connected with 'and'
    expected_kwargs = {"sat:absolute_orbit": 1234, "processing:level": "S2MSIL1C"}
    filter_expr = "filter=sat:absolute_orbit=1234 AND processing:level='S2MSIL1C'"
    await request_valid(
        f"collections/{defaults.collection}/items?bbox={defaults.bbox_csv}&{filter_expr}",
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            geom=defaults.bbox_wkt,
            raise_errors=False,
            count=False,
            validate=True,
            **expected_kwargs,
        ),
    )
    mock_search.reset_mock()

    # with IN
    expected_kwargs = {"instruments": ["MSI"]}
    await request_valid(
        f"collections/{defaults.collection}/items?bbox={defaults.bbox_csv}&filter=instruments IN ('MSI')",
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            geom=defaults.bbox_wkt,
            raise_errors=False,
            count=False,
            validate=True,
            **expected_kwargs,
        ),
    )


@pytest.mark.parametrize(
    "sortby,expected_sort_by",
    [
        ("-datetime", [("start_datetime", "desc")]),
        ("datetime", [("start_datetime", "asc")]),
        ("-start", [("start_datetime", "desc")]),
        ("start", [("start_datetime", "asc")]),
        ("-end", [("end_datetime", "desc")]),
        ("end", [("end_datetime", "asc")]),
    ],
)
async def test_sortby_items_parametrize(request_valid, defaults, sortby, expected_sort_by):
    """Test sortby param with various values."""
    await request_valid(
        f"collections/{defaults.collection}/items?sortby={sortby}",
        expected_search_kwargs={
            "collection": defaults.collection,
            "sort_by": expected_sort_by,
            "token": None,
            "items_per_page": 10,
            "raise_errors": False,
            "count": False,
            "validate": True,
        },
        check_links=False,
    )


async def test_sortby_invalid_field_returns_400(app_client, defaults):
    """Test sortby with an invalid field returns a 400 error and expected error structure."""
    sortby = "-unknownfield"
    response = await app_client.get(f"/collections/{defaults.collection}/items?sortby={sortby}")
    assert response.status_code == 400
    resp_json = response.json()
    assert resp_json["code"] == "400"
    assert "ticket" in resp_json
    assert resp_json["description"] == "Something went wrong"


async def test_search_item_id_from_collection(request_valid, defaults):
    """Search by id through eodag server /collection endpoint should return a valid response"""
    await request_valid(
        f"collections/{defaults.collection}/items/foo",
        expected_search_kwargs={
            "id": "foo",
            "collection": defaults.collection,
            "validate": True,
        },
    )


async def test_cloud_cover_post_search(request_valid, defaults):
    """POST search with cloudCover filtering through eodag server should return a valid response"""
    await request_valid(
        "search",
        method="POST",
        post_data={
            "collections": [defaults.collection],
            "bbox": defaults.bbox_list,
            "query": {"eo:cloud_cover": {"lte": 10}},
        },
        expected_search_kwargs={
            "collection": defaults.collection,
            "token": None,
            "items_per_page": DEFAULT_ITEMS_PER_PAGE,
            "eo:cloud_cover": 10,
            "geom": defaults.bbox_wkt,
            "raise_errors": False,
            "count": False,
            "validate": True,
        },
    )


async def test_intersects_post_search(request_valid, defaults):
    """POST search with intersects filtering through eodag server should return a valid response"""
    await request_valid(
        "search",
        method="POST",
        post_data={
            "collections": [defaults.collection],
            "intersects": defaults.bbox_geojson,
        },
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            geom=defaults.bbox_wkt,
            raise_errors=False,
            count=False,
            validate=True,
        ),
    )


@pytest.mark.parametrize(
    ("input_start", "input_end", "expected_start", "expected_end"),
    [
        ("start", "end", "start", "end"),
        ("start", "..", "start", None),
        ("..", "end", None, "end"),
        ("start", None, "start", "start"),
    ],
)
async def test_date_post_search(request_valid, defaults, input_start, input_end, expected_start, expected_end):
    """POST search with datetime filtering through eodag server should return a valid response"""
    input_date = getattr(defaults, input_start, input_start)
    input_date += f"/{getattr(defaults, input_end, input_end)}" if input_end else ""

    expected_kwargs = {"start": getattr(defaults, expected_start)} if expected_start else {}
    expected_kwargs |= {"end": getattr(defaults, expected_end)} if expected_end else {}

    await request_valid(
        "search",
        method="POST",
        post_data={
            "collections": [defaults.collection],
            "datetime": input_date,
        },
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            raise_errors=False,
            count=False,
            validate=True,
            **expected_kwargs,
        ),
    )


async def test_ids_post_search(request_valid, defaults):
    """POST search with ids filtering through eodag server should return a valid response"""
    await request_valid(
        "search",
        method="POST",
        post_data={
            "collections": [defaults.collection],
            "ids": ["foo", "bar"],
        },
        search_call_count=2,
        expected_search_kwargs=[
            {
                "id": "foo",
                "collection": defaults.collection,
                "validate": True,
            },
            {
                "id": "bar",
                "collection": defaults.collection,
                "validate": True,
            },
        ],
    )


# TODO: add test_provider_prefix_post_search when feature is ready


async def test_search_response_contains_pagination_info(request_valid, defaults):
    """Responses to valid search requests must return a geojson with pagination info in properties"""
    response = await request_valid(f"search?collections={defaults.collection}")
    assert "numberMatched" in response
    assert "numberReturned" in response


@pytest.mark.parametrize(
    ("keep_origin_url", "origin_url_blacklist", "expected_found_alt_urls"),
    [
        (None, None, [False, False, False, False]),
        (True, None, [True, True, True, True]),
        (True, "https://peps.cnes.fr", [False, False, True, False]),
    ],
    ids=[
        "no alt links by default",
        "alt links and no blacklist",
        "alt links and blacklist",
    ],
)
async def test_assets_alt_url_blacklist(
    request_valid,
    defaults,
    mock_search_result,
    keep_origin_url,
    origin_url_blacklist,
    expected_found_alt_urls,
    settings_cache_clear,
):
    """Search through eodag server must not have alternate link if in blacklist"""

    search_result = mock_search_result
    search_result[0].assets.update({"asset1": {"href": "https://peps.cnes.fr"}})
    search_result[1].assets.update({"asset1": {"href": "https://somewhere.fr"}})
    # make assets of the second product available for this test
    search_result[1].properties["order:status"] = ONLINE_STATUS

    with pytest.MonkeyPatch.context() as mp:
        if keep_origin_url is not None:
            mp.setenv("KEEP_ORIGIN_URL", str(keep_origin_url))
        if origin_url_blacklist is not None:
            mp.setenv("ORIGIN_URL_BLACKLIST", origin_url_blacklist)
            mp.setenv("STAC_FASTAPI_LANDING_ID", "aaaaaaaaaaaa")

        response = await request_valid(f"search?collections={defaults.collection}")
        response_items = [f for f in response["features"]]
        assert ["alternate" in a for i in response_items for a in i["assets"].values()] == expected_found_alt_urls


@pytest.mark.parametrize(
    ("method", "url", "post_data", "expected_kwargs"),
    [
        # POST with provider specified
        (
            "POST",
            "search",
            {"collections": ["{defaults.collection}"], "query": {"federation:backends": {"eq": "peps"}}},
            {"provider": "peps"},
        ),
        # POST with no provider specified
        ("POST", "search", {"collections": ["{defaults.collection}"]}, {}),
        # GET with provider specified
        (
            "GET",
            'search?collections={defaults.collection}&query={{"federation:backends":{{"eq":"peps"}} }}',
            None,
            {"provider": "peps"},
        ),
        # GET with no provider specified
        ("GET", "search?collections={defaults.collection}", None, {}),
    ],
    ids=[
        "POST with provider specified",
        "POST with no provider specified",
        "GET with provider specified",
        "GET with no provider specified",
    ],
)
async def test_search_provider_in_downloadlink(request_valid, defaults, method, url, post_data, expected_kwargs):
    """Search through eodag server and check that provider appears in downloadLink"""
    # format defauts values
    url = url.format(defaults=defaults)
    post_data = format_dict_items(post_data, defaults=defaults) if post_data else None

    response = await request_valid(
        url=url,
        method=method,
        post_data=post_data,
        check_links=False,
        expected_search_kwargs=dict(
            token=None,
            items_per_page=10,
            raise_errors=False,
            count=False,
            collection=defaults.collection,
            validate=True,
            **expected_kwargs,
        ),
    )
    response_items = [f for f in response["features"]]
    assert all(
        [i["assets"]["downloadLink"]["href"] for i in response_items if i["properties"]["order:status"] != "orderable"]
    )


@pytest.mark.parametrize("validate", [True, False])
async def test_search_validate(request_valid, defaults, settings_cache_clear, validate):
    """
    Search through eodag server must be validated according to settings
    """
    get_settings().validate_request = validate

    expected_kwargs = {"validate": validate}

    await request_valid(
        f"search?collections={defaults.collection}",
        expected_search_kwargs=dict(
            collection=defaults.collection,
            token=None,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            raise_errors=False,
            count=False,
            **expected_kwargs,
        ),
    )


async def test_search_validate_with_errors(app, app_client, mocker, settings_cache_clear):
    """Search through eodag server must display provider's error if validation fails"""
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
        "GET",
        f"search?collections={collection_id}",
        json=None,
        follow_redirects=True,
        headers={},
    )
    response_content = response.json()

    assert response.status_code == 400
    assert "ticket" in response_content
    response_content.pop("ticket", None)
    assert expected_response == response_content


# ========== PAGINATION TESTS ==========


@pytest.mark.parametrize(
    "method,has_next_token,next_token,expected_next_links",
    [
        ("GET", True, "next_token_123", 1),
        ("GET", False, None, 0),
        ("POST", True, "post_token_123", 1),
        ("POST", False, None, 0),
    ],
    ids=["get_with_next", "get_without_next", "post_with_next", "post_without_next"],
)
async def test_pagination_basic(request_valid, defaults, method, has_next_token, next_token, expected_next_links):
    """Test basic pagination scenarios for GET and POST methods."""
    # Create search result based on whether next token should be present
    if has_next_token:
        search_result = SearchResult(
            [EOProduct("peps", {"id": "_", "collection": "_"})] * 10, next_page_token=next_token
        )
    else:
        search_result = SearchResult([])

    # Set up request parameters based on method
    if method == "GET":
        url = f"search?collections={defaults.collection}&limit=10"
        post_data = None
    else:  # POST
        url = "search"
        post_data = {
            "collections": [defaults.collection],
            "limit": 10,
        }

    response = await request_valid(
        url,
        method=method,
        search_result=search_result,
        post_data=post_data,
        expected_search_kwargs={
            "collection": defaults.collection,
            "token": None,
            "items_per_page": 10,
            "raise_errors": False,
            "count": False,
            "validate": True,
        },
    )

    # Check response links
    assert "links" in response
    next_links = [link for link in response["links"] if link["rel"] == "next"]
    assert len(next_links) == expected_next_links

    if expected_next_links > 0:
        next_link = next_links[0]
        assert next_link["method"] == method
        assert next_link["title"] == "Next page"

        if method == "GET":
            assert f"token={next_token}" in next_link["href"]
        else:  # POST
            assert "body" in next_link
            assert next_link["body"]["token"] == next_token
            assert next_link["body"]["collections"] == [defaults.collection]
            assert next_link["body"]["limit"] == 10


@pytest.mark.parametrize("method", ["GET", "POST"], ids=["get_with_token", "post_with_token"])
async def test_pagination_with_token(request_valid, defaults, method):
    """Test pagination when using existing tokens."""
    current_token = "current_token_123"
    next_token = "next_token_456"

    # Create a mock search result for the next page
    search_result = SearchResult([EOProduct("peps", {"id": "_", "collection": "_"})] * 10, next_page_token=next_token)

    # Set up request parameters based on method
    if method == "GET":
        url = f"search?collections={defaults.collection}&limit=10&token={current_token}"
        post_data = None
    else:  # POST
        url = "search"
        post_data = {
            "collections": [defaults.collection],
            "limit": 10,
            "token": current_token,
        }

    response = await request_valid(
        url,
        method=method,
        search_result=search_result,
        post_data=post_data,
        expected_search_kwargs={
            "collection": defaults.collection,
            "token": current_token,
            "items_per_page": 10,
            "raise_errors": False,
            "count": False,
            "validate": True,
        },
    )

    # Check response has next link with new token
    assert "links" in response
    next_links = [link for link in response["links"] if link["rel"] == "next"]
    assert len(next_links) == 1
    next_link = next_links[0]
    assert next_link["method"] == method

    if method == "GET":
        assert f"token={next_token}" in next_link["href"]
    else:  # POST
        assert "body" in next_link
        assert next_link["body"]["token"] == next_token
        assert next_link["body"]["collections"] == [defaults.collection]
        assert next_link["body"]["limit"] == 10


@pytest.mark.parametrize("method", ["GET", "POST"], ids=["get_with_federation", "post_with_federation"])
async def test_pagination_with_federation_backend(request_valid, defaults, method):
    """Test pagination with federation backend."""
    backend_token = "backend_token_123"

    # Create a mock search result with next page token
    search_result = SearchResult(
        [EOProduct("test_provider", {"id": "_", "collection": "_"})] * 10, next_page_token=backend_token
    )

    # Set up request parameters based on method
    if method == "GET":
        encoded_query = "%7B%22federation%3Abackends%22%3A%7B%22eq%22%3A%22test_provider%22%7D%7D"
        url = f"search?collections={defaults.collection}&limit=10&query={encoded_query}"
        post_data = None
    else:  # POST
        url = "search"
        post_data = {
            "collections": [defaults.collection],
            "limit": 10,
            "query": {"federation:backends": {"eq": "test_provider"}},
        }

    response = await request_valid(
        url,
        method=method,
        search_result=search_result,
        check_links=False,  # Disable link checking to avoid second search call
        post_data=post_data,
        expected_search_kwargs={
            "collection": defaults.collection,
            "token": None,
            "items_per_page": 10,
            "provider": "test_provider",
            "raise_errors": False,
            "count": False,
            "validate": True,
        },
    )

    # Check response has next link with federation backend preserved
    assert "links" in response
    next_links = [link for link in response["links"] if link["rel"] == "next"]
    assert len(next_links) == 1
    next_link = next_links[0]
    assert next_link["method"] == method

    if method == "GET":
        assert f"token={backend_token}" in next_link["href"]
        assert "query=" in next_link["href"]
        assert "federation:backends" in next_link["href"]
        assert "test_provider" in next_link["href"]
    else:  # POST
        assert "body" in next_link
        assert next_link["body"]["token"] == backend_token
        assert next_link["body"]["query"]["federation:backends"]["eq"] == "test_provider"


@pytest.mark.parametrize(
    "method,limit,expected_items_per_page",
    [
        ("GET", None, DEFAULT_ITEMS_PER_PAGE),
        ("GET", 5, 5),
        ("GET", 50, 50),
        ("POST", None, DEFAULT_ITEMS_PER_PAGE),
        ("POST", 5, 5),
        ("POST", 50, 50),
    ],
)
async def test_pagination_limit_handling(request_valid, defaults, method, limit, expected_items_per_page):
    """Test that pagination respects limit parameter for both GET and POST."""
    # Create a mock search result
    search_result = SearchResult(
        [EOProduct("test_provider", {"id": "_", "collection": "_"})] * 10, next_page_token="limit_token_123"
    )

    if method == "GET":
        url = f"search?collections={defaults.collection}"
        if limit is not None:
            url += f"&limit={limit}"
        post_data = None
    else:  # POST
        url = "search"
        post_data = {"collections": [defaults.collection]}
        if limit is not None:
            post_data["limit"] = limit

    response = await request_valid(
        url,
        method=method,
        search_result=search_result,
        post_data=post_data,
        expected_search_kwargs={
            "collection": defaults.collection,
            "token": None,
            "items_per_page": expected_items_per_page,
            "raise_errors": False,
            "count": False,
            "validate": True,
        },
    )

    # Check response has correct next link structure
    assert "links" in response
    next_links = [link for link in response["links"] if link["rel"] == "next"]
    assert len(next_links) == 1
    next_link = next_links[0]

    if method == "GET":
        assert "token=limit_token_123" in next_link["href"]
        if limit is not None:
            assert f"limit={limit}" in next_link["href"]
    else:  # POST
        assert next_link["body"]["token"] == "limit_token_123"
        if limit is not None:
            assert next_link["body"]["limit"] == limit


@pytest.mark.parametrize(
    "pagination_config,expected_token_key",
    [
        ({"next_page_token_key": "custom_token_key"}, "custom_token_key"),
        ({}, "page"),
    ],
    ids=["custom_token_key", "default_fallback"],
)
async def test_next_page_token_key(app_client, defaults, mocker, pagination_config, expected_token_key):
    """Test that next_page_token_key is correctly retrieved from plugin configuration or falls back to default."""

    # Create a mock search plugin with the specified pagination config
    class DummyConfig:
        pagination = pagination_config

    class DummySearchPlugin:
        provider = "test_provider"
        config = DummyConfig()

    # Mock the DAG and its plugins manager
    mock_dag = mocker.Mock()
    mock_plugins_manager = mocker.Mock()
    mock_dag._plugins_manager = mock_plugins_manager
    mock_plugins_manager.get_search_plugins.return_value = iter([DummySearchPlugin()])

    # Mock the search result's next_page method
    mock_search_result = mocker.Mock()
    mock_search_result.next_page.return_value = iter([mocker.Mock()])

    # Mock SearchResult constructor
    mock_search_result_class = mocker.patch("stac_fastapi.eodag.core.SearchResult")
    mock_search_result_class.return_value = mock_search_result

    # Call the function that should use the plugin configuration
    eodag_args = {
        "collection": defaults.collection,
        "items_per_page": 10,
        "raise_errors": False,
        "token": "test_token",
        "provider": "test_provider",
    }

    eodag_search_next_page(dag=mock_dag, eodag_args=eodag_args)

    # Verify that the search plugin was retrieved
    mock_plugins_manager.get_search_plugins.assert_called_once_with(provider="test_provider")

    # Verify SearchResult was created with the expected next_page_token_key
    mock_search_result_class.assert_called_once()
    call_args = mock_search_result_class.call_args
    assert call_args.kwargs["next_page_token_key"] == expected_token_key
    assert call_args.kwargs["next_page_token"] == "test_token"

    # Verify next_page() was called
    mock_search_result.next_page.assert_called_once()
