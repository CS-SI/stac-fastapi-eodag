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

import json
import logging

from eodag import SearchResult
from eodag.utils.exceptions import AuthenticationError, RequestError, TimeOutError, ValidationError


async def test_search_no_results_with_errors(app, app_client, mocker):
    """Search through eodag server must display provider's error if it's empty result"""
    req_err = RequestError("Request error message with status code")
    req_err.status_code = 418
    errors = [
        ("usgs", Exception("Generic exception", "Details of the error")),
        ("theia", TimeOutError("Timeout message")),
        ("peps", req_err),
        ("creodias", AuthenticationError("Authentication message")),
        (
            "onda",
            ValidationError(
                "Validation message: startTimeFromAscendingNode, modificationDate",
                {"startTimeFromAscendingNode", "modificationDate"},
            ),
        ),
    ]
    expected_response = {
        "code": "400",
        "description": "Something went wrong",
        "errors": [
            {
                "provider": "usgs",
                "error": "Exception",
                "message": "Generic exception",
                "detail": "Details of the error",
                "status_code": 500,
            },
            {
                "provider": "theia",
                "error": "TimeOutError",
                "message": "Timeout message",
                "status_code": 504,
            },
            {
                "provider": "peps",
                "error": "RequestError",
                "message": "Request error message with status code",
                "status_code": 400,
            },
            {
                "provider": "creodias",
                "error": "AuthenticationError",
                "message": "Internal server error: please contact the administrator",
                "status_code": 500,
            },
            {
                "provider": "onda",
                "error": "ValidationError",
                "message": "Validation message: start_datetime, updated",
                "detail": {"startTimeFromAscendingNode", "modificationDate"},
                "status_code": 400,
            },
        ],
    }

    mock_search = mocker.patch.object(app.state.dag, "search")
    mock_search.return_value = SearchResult([], 0, errors)

    response = await app_client.request(
        "GET",
        "search?collections=S2_MSI_L1C",
        json=None,
        follow_redirects=True,
        headers={},
    )
    response_content = json.loads(response.content.decode("utf-8"))

    assert response.status_code == 400
    for record in response_content["errors"]:
        if "detail" in record and "{" in record["detail"]:
            record["detail"] = record["detail"].replace("{", "").replace("}", "").replace("'", "")
            record["detail"] = set(s.strip() for s in record["detail"].split(","))
    assert "ticket" in response_content
    response_content.pop("ticket", None)
    assert expected_response == response_content


async def test_auth_error(app_client, mock_search, defaults, caplog):
    """A request to eodag server raising a Authentication error must return a 500 HTTP error code"""
    mock_search.side_effect = AuthenticationError("you are not authorized")
    with caplog.at_level(logging.ERROR):
        response = await app_client.get(f"search?collections={defaults.product_type}", follow_redirects=True)
        response_content = json.loads(response.content.decode("utf-8"))

        assert "description" in response_content
        assert "AuthenticationError" in caplog.text
        assert "you are not authorized" in caplog.text

    assert response.status_code == 500


async def test_timeout_error(app_client, mock_search, defaults, caplog):
    """A request to eodag server raising a Authentication error must return a 500 HTTP error code"""
    mock_search.side_effect = TimeOutError("too long")
    with caplog.at_level(logging.ERROR):
        response = await app_client.get(f"search?collections={defaults.product_type}", follow_redirects=True)
        response_content = json.loads(response.content.decode("utf-8"))

        assert "description" in response_content
        assert "TimeOutError" in caplog.text
        assert "too long" in caplog.text

    assert response.status_code == 504
