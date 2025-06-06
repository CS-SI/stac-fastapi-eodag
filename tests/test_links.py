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
"""Link tests."""

from typing import Literal, Optional
from urllib.parse import parse_qs, urlencode, urlparse
import pytest
from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.testclient import TestClient
from stac_fastapi.eodag.models import links as app_links


@pytest.mark.parametrize("root_path", [""]) 
@pytest.mark.parametrize("prefix", ["", "/stac"])
def tests_app_links(prefix: Literal[''] | Literal['/stac'], root_path: Literal['']):  
    endpoint_prefix = root_path + prefix
    url_prefix = "http://127.0.0.1:8000" + endpoint_prefix

    app = FastAPI(root_path=root_path)
    router = APIRouter(prefix=prefix)
    app.state.router_prefix = router.prefix

    @router.get("/collections")
    async def collections(
        request: Request, 
        extension_names: Optional[list[str]] = Query(None),
        limit: Optional[int] = 10, 
        ):
        query_next = urlencode({"limit": limit, "offset": 10})
        query_prev = urlencode({"limit": limit, "offset": 0})
        query_first = urlencode({"limit": limit, "offset": 0})

        link_next = {
            "rel": "next",
            "body": {"limit": limit, "offset": 10},
            "href": f"./collections?{query_next}",
            "type": "application/geo+json",
            "merge": True,
            "method": "GET",
            "title": "Next page"
        }
        link_prev = {
            "rel": "prev",
            "body": {"limit": limit, "offset": 0},
            "href": f"./collections?{query_prev}",
            "type": "application/geo+json",
            "merge": True,
            "method": "GET",
            "title": "Previous page",
        }
        link_first = {
            "rel": "first",
            "body": {"limit": limit, "offset": 0},
            "href": f"./collections?{query_first}",
            "type": "application/geo+json",
            "merge": True,
            "method": "GET",
            "title": "First page",
        }

        paging_links = app_links.CollectionSearchPagingLinks(
            request, next=link_next, prev=link_prev, first=link_first
        )

        return {
            "url": paging_links.url,
            "base_url": paging_links.base_url,
            "links": paging_links.get_links(extensions=extension_names),
        }

    app.include_router(router)

    with TestClient(
        app,
        base_url="http://127.0.0.1:8000/",
        root_path=root_path,
    ) as client:

        response = client.get(f"{prefix}/collections")
        assert response.status_code == 200
        assert response.json()["url"] == url_prefix + "/collections"
        assert response.json()["base_url"].rstrip("/") == url_prefix
        links = response.json()["links"]
        for link in links:
            if link["rel"] in ["previous", "next", "first"]:
                assert link["method"] == "GET"
            assert link["href"].startswith(url_prefix)
        rels = {link["rel"] for link in links}
        assert "self" in rels
        assert "next" in rels
        assert "previous" in rels

        # Only expect 'first' when offset > 0
        url = response.json()["url"]
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        offset = int(params.get("offset", ["0"])[0])
        if offset > 0:
            assert "first" in rels