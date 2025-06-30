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
"""Operator settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


def get_current_namespace(default="default") -> str:
    """
    Retrieve the current Kubernetes namespace from the service account file.

    :param default: The default namespace to return if the namespace file is not found.
    :type default: str
    :returns: The current namespace as a string.
    :rtype: str
    """
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            ns = f.read().strip()
            if ns:
                return ns
    except FileNotFoundError:
        pass
    return default


class Settings(BaseSettings):
    """Operator settings."""

    repo_url: str

    # Corresponding keys inside ConfigMap data
    product_types_cm_key: str = Field(default="product_types.yml")
    providers_cm_key: str = Field(default="providers.yml")
    eodag_cm_key: str = Field(default="eodag.yml")

    k8s_namespace: str = Field(default_factory=get_current_namespace)

    configmap_name_prefix: str = "eodag-"
    deployment_name: str

    webhook_secret: str = ""

    poll_interval: int = Field(60, description="time in seconds, -1 disables polling")

    clone_dir: str = "/tmp/gitrepo"

    log_level: str = "INFO"
