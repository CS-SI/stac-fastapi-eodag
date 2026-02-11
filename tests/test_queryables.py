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
"""Queryables tests."""

import os
from typing import Annotated, Any, Literal

from pydantic import Field

json_file_path = os.path.join(os.path.dirname(__file__), "resources/datetime.json")


async def test_basic_queryables(request_valid):
    """Response for /queryables request without filters must contain correct fields"""
    res = await request_valid("queryables", check_links=False)
    assert "properties" in res
    assert "collection" in res["properties"]
    assert len(res["properties"]) == 1
    assert "additionalProperties" in res and res["additionalProperties"]
    assert "description" in res and res["description"] == "Queryable names for stac-fastapi."
    assert "title" in res and res["title"] == "STAC queryables for stac-fastapi."
    assert "type" in res and res["type"] == "object"


async def test_collection_queryables(mock_list_queryables, app_client):
    """Response for queryables of specific collection must contain values returned by eodag lib"""
    eodag_response = {
        "product:type": Annotated[
            Literal[tuple(sorted(["SAR", "GRD"]))], Field(default="SAR", **{"title": "Product type"})
        ],
        "start": Annotated[str, Field(..., **{"title": "Start date"})],
        "end": Annotated[str, Field(..., **{"title": "End date"})],
    }
    mock_list_queryables.return_value = eodag_response
    response = await app_client.request(
        method="GET",
        url="/collections/ABC_SAR/queryables",
        follow_redirects=True,
    )
    result = response.json()
    assert "properties" in result
    assert len(result["properties"]) == 2
    assert "product:type" in result["properties"]
    assert result["properties"]["product:type"]["default"] == "SAR"
    assert result["properties"]["product:type"]["enum"] == ["GRD", "SAR"]
    assert "datetime" in result["properties"]
    assert "$ref" not in result, "there is a '$ref' in the /queryables response"


async def test_collection_queryables_with_filters(mock_list_queryables, mock_list_queryables_return_value, app_client):
    """check that queryable filters are correctly sent to eodag"""

    # no additional filters
    def _assert_list_queryables_call(call_args_list: list, params: dict[str, Any]) -> None:
        params_first_call = {k: params[k] for k in ["provider", "collection"] if k in params}
        # first call with only provider and collection
        args, kwargs = call_args_list[0]
        assert params_first_call == kwargs
        # second call with all the parameters
        args, kwargs = call_args_list[1]
        assert params == kwargs

    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables",
        follow_redirects=True,
    )
    _assert_list_queryables_call(mock_list_queryables.call_args_list, {"collection": "ABC_DEF"})
    mock_list_queryables.reset_mock()
    # get queryables for specific provider
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?federation:backends=abc_prod",
        follow_redirects=True,
    )
    _assert_list_queryables_call(mock_list_queryables.call_args_list, {"collection": "ABC_DEF", "provider": "abc_prod"})
    mock_list_queryables.reset_mock()
    # queryables with filter that does not have to be changed
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?emcwf:year=2000",
        follow_redirects=True,
    )
    _assert_list_queryables_call(mock_list_queryables.call_args_list, {"collection": "ABC_DEF", "emcwf:year": ["2000"]})
    mock_list_queryables.reset_mock()
    # queryables with two values of the same filter param
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?emcwf:year=2000&emcwf:year=2001",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "emcwf:year": ["2000", "2001"]},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter that has to be changed to eodag param
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?sat:absolute_orbit=10",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "sat:absolute_orbit": ["10"]},
    )
    mock_list_queryables.reset_mock()
    # queryables with datetime filter
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?datetime=2020-01-01T00:00:00Z",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "start_datetime": "2020-01-01T00:00:00Z"},
    )
    mock_list_queryables.reset_mock()
    # queryables with invalid datetime filter
    response = await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?datetime=2020-01-01T00:0:00Z",
        follow_redirects=True,
    )
    assert response.status_code == 400
    mock_list_queryables.reset_mock()
    # queryables with filter of type list of literals
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?ecmwf:variable=ammonia&ecmwf:variable=carbon_monoxide",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "ecmwf:variable": ["ammonia", "carbon_monoxide"]},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter of type list of literals and a single value is given
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?ecmwf:variable=ammonia",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "ecmwf:variable": ["ammonia"]},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter of type list of literals and no value is given
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?ecmwf:variable",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "ecmwf:variable": [""]},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter of type literal string
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?ecmwf:data_format=grib",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "ecmwf:data_format": "grib"},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter of type literal string: use last value
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?ecmwf:data_format=grib&ecmwf:data_format=netcdf_zip",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "ecmwf:data_format": "netcdf_zip"},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter of type literal string and no value is given
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?ecmwf:data_format",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "ecmwf:data_format": ""},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter of type tuple
    # Note: we cannot test here if a value is missing from the tuple, this can be done in the
    #       test of the `list_queryables` function in EODAG.
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?ecmwf:area=10&ecmwf:area=40&ecmwf:area=12&ecmwf:area=42",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "ecmwf:area": ["10", "40", "12", "42"]},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter of type string
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?start_datetime=2020-01-01T00:00:00Z&end_datetime=2020-01-31T00:00:00Z",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "start_datetime": "2020-01-01T00:00:00Z", "end_datetime": "2020-01-31T00:00:00Z"},
    )
    mock_list_queryables.reset_mock()
    # queryables with filter by alias (alias as AliasChoices)
    # Note: we know the alias is found in the queryables if the values are adapted to literal strings.
    # Expected calls:
    # * "ecmwf_data_format" is of type literal string -> adapted to string.
    # * "foo" is not found in the queryables -> pass it as list.
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?ecmwf_data_format=grib&date=2026-02-04&foo=boo",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "ecmwf_data_format": "grib", "date": "2026-02-04", "foo": ["boo"]},
    )
    mock_list_queryables.reset_mock()
    # more filters by alias (alias as string, no alias)
    # "dolorem" by field name; "ips" by alias; "bar" has no alias
    # Note: again we expect the values to be adapted to strings
    await app_client.request(
        method="GET",
        url="/collections/ABC_DEF/queryables?dolorem=val_1&ips=val_2&bar=val_3",
        follow_redirects=True,
    )
    _assert_list_queryables_call(
        mock_list_queryables.call_args_list,
        {"collection": "ABC_DEF", "dolorem": "val_1", "ips": "val_2", "bar": "val_3"},
    )


async def test_default_in_collection_queryables(
    defaults,
    app_client,
    mock_stac_discover_queryables,
    mock_token_authenticate,
    mock_oidc_refresh_token_base_init,
    mock_oidc_token_exchange_auth_authenticate,
):
    """The queryables should not have default value set to null."""
    response = await app_client.get(f"/collections/{defaults.collection}/queryables", follow_redirects=True)
    resp_json = response.json()
    for _, value in resp_json["properties"].items():
        if "default" in value:
            assert value.get("default") is not None, "The 'default' field in the /queryables response must not be null."
