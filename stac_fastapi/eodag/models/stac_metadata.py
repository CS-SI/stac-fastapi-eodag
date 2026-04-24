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
"""property fields."""

from typing import Any

from fastapi import Request


def get_federation_backend_dict(request: Request, provider_name: str) -> dict[str, Any]:
    """Generate Federation backend dict

    :param request: FastAPI request
    :param provider_name: provider name
    :return: Federation backend dictionary
    """
    provider = next(
        p for p in request.app.state.dag.providers.values() if provider_name in [p.name, getattr(p, "group", None)]
    )
    return {
        "title": provider.group or provider.name,
        "description": provider.title,
        "url": provider.url,
    }
