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

from stac_fastapi.eodag.constants import DEFAULT_ITEMS_PER_PAGE


async def test_request_params(request_valid, request_not_valid, tested_product_type):
    """
    Test the request parameters for the search endpoint.
    """
    await request_not_valid(f"search?collections={tested_product_type}&bbox=1")
    await request_not_valid(f"search?collections={tested_product_type}&bbox=0,43,1")
    await request_not_valid(f"search?collections={tested_product_type}&bbox=0,,1")
    await request_not_valid(f"search?collections={tested_product_type}&bbox=a,43,1,44")

    await request_valid(
        f"search?collections={tested_product_type}",
        expected_search_kwargs=dict(
            productType=tested_product_type,
            page=1,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            raise_errors=False,
            count=True,
        ),
    )
    await request_valid(
        f"search?collections={tested_product_type}&bbox=0,43,1,44",
        expected_search_kwargs=dict(
            productType=tested_product_type,
            page=1,
            items_per_page=DEFAULT_ITEMS_PER_PAGE,
            geom="POLYGON ((0.0 43.0, 1.0 43.0, 1.0 44.0, 0.0 44.0, 0.0 43.0))",
            raise_errors=False,
            count=True,
        ),
    )


async def test_items_response(request_valid, tested_product_type):
    """Returned items properties must be mapped as expected"""
    resp_json = await request_valid(
        f"search?collections={tested_product_type}",
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
    assert first_props["datetime"] == "2018-02-15T23:53:22.871000+00:00"
    assert first_props["start_datetime"] == "2018-02-15T23:53:22.871000+00:00"
    assert first_props["end_datetime"] == "2018-02-16T00:12:14.035000+00:00"
    assert first_props["license"] == "other"
    assert first_props["platform"] == "S1A"
    assert first_props["instruments"] == ["SAR-C", "SAR"]
    assert first_props["eo:cloud_cover"] == 0
    assert first_props["sat:absolute_orbit"] == 20624
    assert first_props["product:type"] == "OCN"
    assert first_props["storage:tier"] == "succeeded"
    assert res[1]["properties"]["storage:tier"] == "orderable"


async def test_not_found(request_not_found, disable_product_types_fetch):
    """A request to eodag server with a not supported product type must return a 404 HTTP error code"""
    await request_not_found("search?collections=ZZZ&bbox=0,43,1,44")
