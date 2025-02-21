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
"""eodag-fastapi tests."""

from __future__ import annotations

import contextlib
import os

TEST_RESOURCES_PATH = os.path.join(os.path.dirname(__file__), "resources")


@contextlib.contextmanager
def temporary_environment(**env_vars):
    """
    A context manager to temporarily set environment variables.
    """
    # Save the original environment variables
    original_env = os.environ.copy()

    # Set the new temporary environment variables
    os.environ.update(env_vars)

    try:
        yield
    finally:
        # Restore the original environment variables
        os.environ.clear()
        os.environ.update(original_env)
