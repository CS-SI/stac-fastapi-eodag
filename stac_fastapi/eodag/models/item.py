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
"""stac item."""

from typing import Any, Optional
from urllib.parse import quote, unquote_plus, urlparse

import orjson
from fastapi import Request
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.stac import Item

from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import ONLINE_STATUS
from eodag.utils import deepcopy, guess_file_type
from stac_fastapi.eodag.config import Settings, get_settings
from stac_fastapi.eodag.errors import MisconfiguredError
from stac_fastapi.eodag.models.links import ItemLinks


def _get_retrieve_body_for_order(order_link: str) -> dict[str, Any]:
    """Return the body of the request used to order a product."""
    parts = urlparse(order_link)
    keys = ["request", "inputs", "location"]  # keys used by different providers
    request_dict = orjson.loads(parts.query)
    retrieve_body = None
    for key in keys:
        if key in request_dict:
            retrieve_body = request_dict[key]
    if isinstance(retrieve_body, str):  # order link is quoted json or url
        try:
            retrieve_body = orjson.loads(unquote_plus(retrieve_body))
        except ValueError:  # string is a url not a geojson -> no body required
            retrieve_body = {}
    elif not isinstance(retrieve_body, dict):
        raise MisconfiguredError("order_link must include a dict with key request, inputs or location")
    return retrieve_body


def create_stac_item(
    product: EOProduct,
    request: Request,
    extension_names: Optional[list[str]],
    request_json: Optional[Any] = None,
) -> Item:
    """Create a STAC item from an EODAG product"""
    if product.collection is None:
        raise NotFoundError("A STAC item can not be created from an EODAG EOProduct without collection")

    settings: Settings = get_settings()

    feature = product.as_dict()
    properties = feature["properties"]
    assets = feature["assets"]
    provider = properties["federation:backends"][0]
    collection = feature["collection"]
    enabled_extensions = set(extension_names or [])

    download_base_url = settings.download_base_url or get_base_url(request)

    quoted_id = quote(feature["id"])
    asset_proxy_url = (
        (download_base_url + f"data/{provider}/{collection}/{quoted_id}")
        if "DataDownload" in enabled_extensions
        else None
    )

    auto_order_whitelist = settings.auto_order_whitelist
    if provider in auto_order_whitelist:
        # a product from a whitelisted federation backend is considered as online
        properties["order:status"] = ONLINE_STATUS

    keep_origin_url = settings.keep_origin_url
    origin_url_blacklist = tuple(settings.origin_url_blacklist)

    if asset_proxy_url:
        for asset_name, asset in assets.items():
            should_keep_origin = keep_origin_url and not asset["href"].startswith(origin_url_blacklist)
            origin = deepcopy(asset) if should_keep_origin else None

            asset["href"] = f"{asset_proxy_url}/{quote(asset_name)}"
            asset.pop("storage:refs", None)

            if origin:
                asset["alternate"] = {"origin": origin}

    # TODO: remove downloadLink asset after EODAG assets rework
    has_parquet_asset = any(asset_name.endswith(".parquet") for asset_name in assets)
    if (download_link := properties.get("eodag:download_link")) and not has_parquet_asset:
        origin_href = download_link
        proxied_href = f"{asset_proxy_url}/downloadLink" if asset_proxy_url else origin_href
        mime_type = guess_file_type(origin_href) or "application/octet-stream"

        download_asset = {"title": "Download link", "href": proxied_href, "type": mime_type, "roles": ["data"]}

        if asset_proxy_url and keep_origin_url and not origin_href.startswith(origin_url_blacklist):
            download_asset["alternate"] = {
                "origin": {
                    "title": "Origin asset link",
                    "href": origin_href,
                    "type": mime_type,
                },
            }

        assets["downloadLink"] = download_asset

    # filter properties we do not want to expose
    feature["properties"] = {k: v for k, v in properties.items() if not k.startswith("eodag:")}
    feature["properties"].pop("qs", None)

    link_extensions = list(enabled_extensions)
    if "CollectionOrderExtension" in enabled_extensions:
        is_orderable = (
            bool(properties.get("eodag:order_link")) and feature["properties"].get("order:status") == "orderable"
        )
        if provider in auto_order_whitelist or not is_orderable:
            link_extensions.remove("CollectionOrderExtension")

    # get request body for retrieve link (if product has to be ordered)
    retrieve_body = (
        _get_retrieve_body_for_order(order_link) if (order_link := properties.get("eodag:order_link")) else {}
    )

    collection_obj = request.app.state.dag.collections_config.get(product.collection)
    collection_title = (collection_obj.title if collection_obj else None) or collection

    feature["links"] = ItemLinks(
        collection_id=collection,
        collection_title=collection_title,
        item_id=quoted_id,
        retrieve_body=retrieve_body,
        request=request,
    ).get_links(extensions=link_extensions, extra_links=feature.get("links"), request_json=request_json)

    return feature
