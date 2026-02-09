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

from typing import Any, Callable, Optional
from urllib.parse import quote, unquote_plus, urlparse

import orjson
from fastapi import Request
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.stac import Item
from stac_pydantic.api.version import STAC_API_VERSION
from stac_pydantic.shared import Asset

from eodag.api.product._product import EOProduct
from eodag.api.product.metadata_mapping import OFFLINE_STATUS, ONLINE_STATUS
from eodag.utils import deepcopy, guess_file_type
from stac_fastapi.eodag.config import Settings, get_settings
from stac_fastapi.eodag.errors import MisconfiguredError
from stac_fastapi.eodag.models.links import ItemLinks
from stac_fastapi.eodag.models.stac_metadata import CommonStacMetadata


def _get_retrieve_body_for_order(product: EOProduct) -> dict[str, Any]:
    """returns the body of the request used to order a product"""
    parts = urlparse(product.properties["eodag:order_link"])
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
    model: type[CommonStacMetadata],
    extension_is_enabled: Callable[[str], bool],
    request: Request,
    extension_names: Optional[list[str]],
    request_json: Optional[Any] = None,
) -> Item:
    """Create a STAC item from an EODAG product"""
    if product.collection is None:
        raise NotFoundError("A STAC item can not be created from an EODAG EOProduct without collection")

    settings: Settings = get_settings()

    collection_obj = request.app.state.dag.collections_config.get(product.collection)
    collection = collection_obj.id if collection_obj else product.collection

    feature = Item(
        type="Feature",
        assets={},
        id=product.properties["id"],
        geometry=product.geometry.__geo_interface__,
        bbox=product.geometry.bounds,
        collection=collection,
        stac_version=STAC_API_VERSION,
    )

    stac_extensions: set[str] = set()

    download_base_url = settings.download_base_url
    if not download_base_url:
        download_base_url = get_base_url(request)

    quoted_id = quote(feature["id"])
    asset_proxy_url = (
        (download_base_url + f"data/{product.provider}/{collection}/{quoted_id}")
        if extension_is_enabled("DataDownload")
        else None
    )

    settings = get_settings()
    auto_order_whitelist = settings.auto_order_whitelist
    if product.provider in auto_order_whitelist:
        # a product from a whitelisted federation backend is considered as online
        product.properties["order:status"] = ONLINE_STATUS

    # create assets only if product is not offline
    if (
        product.properties.get("order:status", ONLINE_STATUS) != OFFLINE_STATUS
        or product.provider in auto_order_whitelist
    ):
        for k, v in product.assets.items():
            # TODO: download extension with origin link (make it optional ?)
            asset_model = Asset.model_validate(v)
            feature["assets"][k] = asset_model.model_dump(exclude_none=True)

            if asset_proxy_url:
                origin = deepcopy(feature["assets"][k])
                quoted_key = quote(k)
                feature["assets"][k]["href"] = asset_proxy_url + "/" + quoted_key

                origin_href = origin.get("href")
                if (
                    settings.keep_origin_url
                    and origin_href
                    and not origin_href.startswith(tuple(settings.origin_url_blacklist))
                ):
                    feature["assets"][k]["alternate"] = {"origin": origin}

        # TODO: remove downloadLink asset after EODAG assets rework
        if download_link := product.properties.get("eodag:download_link"):
            origin_href = download_link
            if asset_proxy_url:
                download_link = asset_proxy_url + "/downloadLink"

            mime_type = guess_file_type(origin_href) or "application/octet-stream"

            feature["assets"]["downloadLink"] = {
                "title": "Download link",
                "href": download_link,
                # TODO: download link is not always a ZIP archive
                "type": mime_type,
            }

            if settings.keep_origin_url and not origin_href.startswith(tuple(settings.origin_url_blacklist)):
                feature["assets"]["downloadLink"]["alternate"] = {
                    "origin": {
                        "title": "Origin asset link",
                        "href": origin_href,
                        # TODO: download link is not always a ZIP archive
                        "type": mime_type,
                    },
                }
        if "zarr" in product.assets and asset_proxy_url:
            feature["assets"]["Zarr index"] = {
                "title": "Zarr store index",
                "href": asset_proxy_url + "/zarr/index",
                "type": "application/json",
            }

    feature_model = model.model_validate(
        {
            **product.properties,
            **{"federation:backends": [product.provider], "storage:tier": product.properties.get("order:status")},
        }
    )
    stac_extensions.update(feature_model.get_conformance_classes())

    # filter properties we do not want to expose
    feature["properties"] = {
        k: v for k, v in feature_model.model_dump(exclude_none=True).items() if not k.startswith("eodag:")
    }
    feature["properties"].pop("qs", None)

    feature["stac_extensions"] = list(stac_extensions)

    if extension_names and product.provider not in auto_order_whitelist:
        if "CollectionOrderExtension" in extension_names and (
            not product.properties.get("eodag:order_link", False)
            or feature["properties"].get("order:status", "") != "orderable"
        ):
            extension_names.remove("CollectionOrderExtension")
    else:
        extension_names = []

    # get request body for retrieve link (if product has to be ordered)
    if "eodag:order_link" in product.properties:
        retrieve_body = _get_retrieve_body_for_order(product)
    else:
        retrieve_body = {}

    if eodag_args := getattr(request.state, "eodag_args", None):
        if provider := eodag_args.get("provider", None):
            retrieve_body["federation:backends"] = [provider]

    feature["links"] = ItemLinks(
        collection_id=collection,
        item_id=quoted_id,
        retrieve_body=retrieve_body,
        request=request,
    ).get_links(extensions=extension_names, extra_links=feature.get("links"), request_json=request_json)

    return feature
