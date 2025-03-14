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
"""requirement tests."""

import ast
import configparser
import os
import re
import sys
from typing import Any, Iterator

from eodag.utils.exceptions import MisconfiguredError
from importlib_metadata import distributions, packages_distributions, requires
from packaging.requirements import Requirement
from stdlib_list import stdlib_list

project_path = "./stac_fastapi"
project_name = "stac_fastapi.eodag"


def get_imports(filepath: str) -> Iterator[Any]:
    """Get python imports from the given file path"""
    with open(filepath, "r") as file:
        try:
            root = ast.parse(file.read())
        except UnicodeDecodeError as e:
            raise MisconfiguredError(
                f"UnicodeDecodeError in {filepath}: {e.object[max(e.start - 50, 0) : min(e.end + 50, len(e.object))]!r}"
            ) from e

    for node in ast.iter_child_nodes(root):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "utils":
                    pass

                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            if node.module.split(".")[0] == "utils":
                pass
            yield node.module.split(".")[0]


def get_project_imports(project_path: str) -> set[str]:
    """Get python imports from the project path"""
    imports: set[str] = set()
    for dirpath, _, files in os.walk(project_path):
        for filename in files:
            if filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)
                imports.update(get_imports(filepath))
    return imports


def get_self_dependencies(extras=None):
    """Get the main dependencies (excluding optional dependencies and version constraints)."""
    for dist in distributions():
        # Ensures it's the local project
        if dist.locate_file("pyproject.toml").exists():
            package_name = dist.metadata["Name"]
            raw_deps = requires(package_name) or []

            clean_deps = set()
            for dep in raw_deps:
                dep_split = dep.split("; extra ==")
                # Skip unwanted optional dependencies
                if len(dep_split) > 1 and (extras is None or dep_split[-1].strip(" \"'") not in extras):
                    continue

                # Remove extras conditions (e.g., "; extra == 'some-feature'")
                dep = dep.split(";")[0]
                # Remove version constraints
                dep = re.split(r"[<>=!~]", dep, maxsplit=1)[0].strip()
                # Remove optional extras (e.g., "tqdm[notebook]" → "tqdm")
                dep = dep.split("[")[0].strip()
                clean_deps.add(dep)

            # Sorted for consistency
            return sorted(clean_deps)

    return []


def get_optional_dependencies(setup_cfg_path: str, extra: str) -> set[str]:
    """Get extra requirements from the given setup.cfg file path"""
    config = configparser.ConfigParser()
    config.read(setup_cfg_path)
    deps = set()
    for req in config["options.extras_require"][extra].split("\n"):
        if req.startswith("eodag["):
            for found_extra in re.findall(r"([\w-]+)[,\]]", req):
                deps.update(get_optional_dependencies(setup_cfg_path, found_extra))
        elif req:
            deps.add(Requirement(req).name)

    return deps


def test_all_requirements():
    """Needed libraries must be in project requirements"""

    project_imports = get_project_imports(project_path)
    setup_requires = get_self_dependencies(["observability"])
    import_required_dict = packages_distributions()
    try:
        default_libs = stdlib_list()
    except FileNotFoundError:
        # python version might not be supported by `stdlib_list`
        # Since python3.10, we can use `sys.stdlib_module_names` instead
        default_libs = list(sys.stdlib_module_names)

    missing_imports = []
    for project_import in project_imports:
        required = import_required_dict.get(project_import, [project_import])
        if not set(required).intersection(setup_requires) and project_import not in default_libs:
            missing_imports.append(project_import)

    assert len(missing_imports) == 0, (
        f"The following libraries were not found in project requirements: {missing_imports}"
    )
