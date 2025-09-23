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
"""link helpers."""

from typing import Any, Optional
from urllib.parse import ParseResult, parse_qs, unquote, urlencode, urljoin, urlparse

import attr
from stac_fastapi.types.requests import get_base_url
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes
from starlette.requests import Request

# These can be inferred from the item/collection so they aren't included in the database
# Instead they are dynamically generated when querying the database using the classes defined below
INFERRED_LINK_RELS = ["self", "item", "collection"]


def filter_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove inferred links."""
    return [link for link in links if link["rel"] not in INFERRED_LINK_RELS]


def merge_params(url: str, newparams: dict[str, list[str]]) -> str:
    """Merge url parameters."""
    u = urlparse(url)
    params = parse_qs(u.query)
    params.update(newparams)
    param_string = unquote(urlencode(params, True))

    href = ParseResult(
        scheme=u.scheme,
        netloc=u.netloc,
        path=u.path,
        params=u.params,
        query=param_string,
        fragment=u.fragment,
    ).geturl()
    return href


@attr.s
class BaseLinks:
    """Create inferred links common to collections and items."""

    request: Request = attr.ib()

    @property
    def base_url(self):
        """Get the base url."""
        return get_base_url(self.request)

    @property
    def url(self):
        """Get the current request url."""
        return str(self.request.url)

    def resolve(self, url: Any):
        """Resolve url to the current request url."""
        return urljoin(str(self.base_url), str(url))

    def link_self(self) -> dict[str, str]:
        """Return the self link."""
        return {"rel": Relations.self.value, "type": MimeTypes.json.value, "href": self.url, "title": "Current Page"}

    def create_links(self, extensions: list[str]) -> list[dict[str, Any]]:
        """Return all inferred links."""
        links: list[dict[str, Any]] = []
        for name in dir(self):
            if name.startswith("link_") and callable(getattr(self, name)):
                link = getattr(self, name)()
                if link is not None:
                    links.append(link)
            elif name.startswith("links_") and callable(getattr(self, name)):
                new_links = getattr(self, name)()
                if new_links is not None:
                    links.extend(new_links)
            elif "extension_link" in name and callable(getattr(self, name)):
                extension_snake = name.split("_link")[0]
                extension_name = "".join(word.capitalize() for word in extension_snake.split("_"))
                if extension_name in extensions:
                    link = getattr(self, name)()
                    if link is not None:
                        links.append(link)
        return links

    def get_links(
        self,
        extensions: list[str],
        extra_links: Optional[list[dict[str, Any]]] = None,
        request_json: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Generate all the links.

        Get the links object for a stac resource by iterating through
        available methods on this class that start with link_.
        """
        if self.request.method == "POST":
            self.request.state.postbody = request_json
        # join passed in links with generated links
        # and update relative paths
        links = self.create_links(extensions)

        if extra_links:
            # For extra links passed in,
            # add links modified with a resolved href.
            # Drop any links that are dynamically
            # determined by the server (e.g. self, item, etc.)
            # Resolving the href allows for relative paths
            # to be stored in pgstac and for the hrefs in the
            # links of response STAC objects to be resolved
            # to the request url.
            links += [
                {**link, "href": self.resolve(link["href"])}
                for link in extra_links
                if link["rel"] not in INFERRED_LINK_RELS
            ]

        return links


@attr.s
class PagingLinks(BaseLinks):
    """Create links for paging."""

    next: Optional[int] = attr.ib(kw_only=True, default=None)

    def link_next(self) -> Optional[dict[str, Any]]:
        """Create link for next page."""
        if self.next is not None:
            method = self.request.method
            if method == "GET":
                href = merge_params(self.url, {"page": [str(self.next)]})
                return {
                    "rel": Relations.next.value,
                    "type": MimeTypes.geojson.value,
                    "method": method,
                    "href": href,
                    "title": "Next page",
                }
            if method == "POST":
                return {
                    "rel": Relations.next,
                    "type": MimeTypes.geojson,
                    "method": method,
                    "href": f"{self.request.url}",
                    "body": {**self.request.state.postbody, "page": self.next},
                    "title": "Next page",
                }

        return None


@attr.s
class CollectionSearchPagingLinks(BaseLinks):
    """Create links for paging in collection search results."""

    next: Optional[dict[str, Any]] = attr.ib(kw_only=True, default=None)
    prev: Optional[dict[str, Any]] = attr.ib(kw_only=True, default=None)
    first: Optional[dict[str, Any]] = attr.ib(kw_only=True, default=None)

    def link_next(self) -> Optional[dict[str, Any]]:
        """Create link for next page."""
        if self.next is not None:
            href = merge_params(self.url, self.next["body"])

            # if next link is equal to this link, skip it
            if href == self.url:
                return None

            return {
                "rel": Relations.next.value,
                "type": MimeTypes.geojson.value,
                "href": href,
                "title": "Next page",
            }

        return None

    def link_prev(self) -> Optional[dict[str, Any]]:
        """Create link for previous page."""
        if self.prev is not None:
            href = merge_params(self.url, self.prev["body"])

            # if prev link is equal to this link, skip it
            if href == self.url:
                return None

            return {
                "rel": Relations.previous.value,
                "type": MimeTypes.geojson.value,
                "href": href,
                "title": "Previous page",
            }

        return None

    def link_first(self) -> Optional[dict[str, Any]]:
        """Create link for first page."""
        if self.first is not None:
            u = urlparse(self.url)
            params = parse_qs(u.query)

            offset_value = params.get("offset", ["0"])
            offset = int(offset_value[0])

            if offset == 0:
                return None

            href = merge_params(self.url, self.first["body"])

            return {
                "rel": "first",
                "type": MimeTypes.geojson.value,
                "href": href,
                "title": "First page",
            }

        return None


@attr.s
class CollectionLinksBase(BaseLinks):
    """Create inferred links specific to collections."""

    collection_id: str = attr.ib()

    def collection_link(self, rel: str = Relations.collection.value) -> dict[str, str]:
        """Create a link to a collection."""
        return {
            "rel": rel,
            "type": MimeTypes.json.value,
            "href": self.resolve(f"collections/{self.collection_id}"),
            "title": f"{self.collection_id}",
        }


@attr.s
class CollectionLinks(CollectionLinksBase):
    """Create inferred links specific to collections."""

    def link_self(self) -> dict[str, str]:
        """Return the self link."""
        return self.collection_link(rel=Relations.self.value)

    def link_items(self) -> dict[str, str]:
        """Create the `item` link."""
        return {
            "rel": "items",
            "type": MimeTypes.geojson.value,
            "href": self.resolve(f"collections/{self.collection_id}/items"),
            "title": "Items",
        }

    def filter_extension_link_queryables(self) -> dict[str, str]:
        """Create the `queryables` link."""
        return {
            "rel": "http://www.opengis.net/def/rel/ogc/1.0/queryables",
            "type": MimeTypes.jsonschema.value,
            "href": self.resolve(f"collections/{self.collection_id}/queryables"),
            "title": "Queryables",
        }

    def collection_order_extension_link_retrieve(self) -> dict[str, Any]:
        """Create the `retrieve` links for the collection."""
        return {
            "rel": "retrieve",
            "type": MimeTypes.geojson.value,
            "href": self.resolve(f"collections/{self.collection_id}/order"),
            "method": "POST",
            "title": "Retrieve",
        }


@attr.s
class ItemCollectionLinks(CollectionLinksBase):
    """Create inferred links specific to collections."""

    def link_self(self) -> dict[str, str]:
        """Return the self link."""
        return {
            "rel": Relations.self.value,
            "type": MimeTypes.geojson.value,
            "href": self.resolve(f"collections/{self.collection_id}/items"),
            "title": "Items",
        }

    def link_collection(self) -> dict[str, str]:
        """Create the `collection` link."""
        return self.collection_link()


@attr.s
class ItemLinks(CollectionLinksBase):
    """Create inferred links specific to items."""

    item_id: str = attr.ib()
    retrieve_body: Optional[dict[str, Any]] = attr.ib()

    def link_self(self) -> dict[str, str]:
        """Create the self link."""
        query_string = ""
        validate = self.retrieve_body.get("validate", None)
        if validate is not None:
            query_string = f"?validate={validate}"

        return {
            "rel": Relations.self.value,
            "type": MimeTypes.geojson.value,
            "href": self.resolve(f"collections/{self.collection_id}/items/{self.item_id}{query_string}"),
            "title": "Original item link",
        }

    def link_collection(self) -> dict[str, str]:
        """Create the `collection` link."""
        return self.collection_link()

    def collection_order_extension_link_retrieve(self) -> Optional[dict[str, Any]]:
        """Create the `retrieve` link."""
        href = self.resolve(f"collections/{self.collection_id}/order")
        link = {
            "rel": "retrieve",
            "type": MimeTypes.geojson.value,
            "href": href,
            "method": "POST",
            "title": "Retrieve",
        }
        if self.retrieve_body:
            link["body"] = self.retrieve_body

        return link
