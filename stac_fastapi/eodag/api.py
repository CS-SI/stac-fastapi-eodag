"""override stac api for download handlers."""

# -*- coding: utf-8 -*-
# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
#
# This file is part of EODAG project
#     https://www.github.com/CS-SI/EODAG
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
from typing import Type

import attr
from pydantic import BaseModel
from stac_fastapi.api.app import StacApi

from stac_fastapi.eodag.models.stac_metadata import CommonStacMetadata


@attr.s
class EodagStacApi(StacApi):
    """Override default API to include download endpoints handlers."""

    item_properties_model: Type[BaseModel] = attr.ib(default=CommonStacMetadata)

    # def register_download_item(self) -> None:
    #     """Register download item endpoint (GET /collections/{collection_id}/items/{item_id}/download).

    #     Returns:
    #         None
    #     """
    #     self.router.add_api_route(
    #         name="Download Item",
    #         path="/collections/{collection_id}/items/{item_id}/download",
    #         response_class=StreamingResponse,
    #         methods=["GET"],
    #         endpoint=create_async_endpoint(
    #             self.client.download_item, ItemUri, StreamingResponse
    #         ),
    #     )

    # def register_core(self) -> None:
    #     """Register endpoints."""
    #     super().register_core()
    #     self.register_download_item()
