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
"""app tests."""

import json


async def test_route(request_valid):
    """Test the root route."""
    await request_valid("/")


async def test_forward(app_client):
    """Test the root route with Forwarded and X-Forwarded-* headers."""
    response = await app_client.get("/", follow_redirects=True)
    assert 200 == response.status_code
    resp_json = json.loads(response.content.decode("utf-8"))
    assert resp_json["links"][0]["href"] == "http://testserver/"

    response = await app_client.get("/", follow_redirects=True, headers={"Forwarded": "host=foo;proto=https"})
    assert 200 == response.status_code
    resp_json = json.loads(response.content.decode("utf-8"))
    assert resp_json["links"][0]["href"] == "https://foo/"

    response = await app_client.get(
        "/",
        follow_redirects=True,
        headers={"X-Forwarded-Host": "bar", "X-Forwarded-Proto": "httpz"},
    )
    assert 200 == response.status_code
    resp_json = json.loads(response.content.decode("utf-8"))
    assert resp_json["links"][0]["href"] == "httpz://bar/"


async def test_liveness_probe(app_client):
    """stac-fastap liveliness/readiness probe."""

    response = await app_client.get("/_mgmt/ping")
    assert 200 == response.status_code
    assert response.json()["message"] == "PONG"


async def test_conformance(request_valid):
    """Request to /conformance should return a valid response"""
    await request_valid("conformance", check_links=False)


async def test_service_desc(request_valid):
    """Request to service_desc should return a valid response"""
    service_desc = await request_valid("api", check_links=False)
    assert "openapi" in service_desc.keys()
    assert service_desc["info"]["title"] == "FastAPI"
    assert len(service_desc["paths"].keys()) >= 0
    # test a 2nd call (ending slash must be ignored)
    await request_valid("api/", check_links=False)


async def test_service_doc(app_client):
    """Request to service_doc should return a valid response"""
    response = await app_client.get("api.html", follow_redirects=True)
    assert 200 == response.status_code
