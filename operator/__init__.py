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
"""Kubernetes operator tracking config changes and triggering rollouts."""

import asyncio
import logging
import os
from operator.config import Settings
from typing import AsyncGenerator, Dict, Optional

import git
import yaml
from eodag import EODataAccessGateway
from eodag.utils import load_yaml
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.concurrency import asynccontextmanager
from kubernetes import client
from kubernetes import config as k8s_config

settings = Settings()

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("eodag-operator")


app = FastAPI()


last_commit_hash: Optional[str] = None


def load_kube_config():
    """Load Kubernetes configuration, preferring in-cluster config and falling back to local config."""
    try:
        k8s_config.load_incluster_config()
        logger.debug("Loaded in-cluster kube config.")
    except Exception:
        k8s_config.load_kube_config()
        logger.debug("Loaded local kube config.")


def get_watched_files_map() -> dict[str, str]:
    """
    Build a map of file paths (from env vars) to their ConfigMap keys.
    Only include entries where env var is set.
    Raise FileNotFoundError if path is set but file does not exist.
    """
    watched_map = {}

    env_to_cm = {
        "EODAG_PRODUCT_TYPES_CFG_FILE": settings.product_types_cm_key,
        "EODAG_PROVIDERS_CFG_FILE": settings.providers_cm_key,
        "EODAG_CFG_FILE": settings.eodag_cm_key,
    }

    for env_var, cm_key in env_to_cm.items():
        path = os.getenv(env_var)
        if path:
            if not os.path.isfile(path):
                logger.error(f"Config file set in {env_var} but file does not exist: {path}")
                raise FileNotFoundError(f"Config file set in {env_var} but file does not exist: {path}")
            logger.info(f"Loaded config path from env {env_var}: {path}")
            watched_map[path] = cm_key
        else:
            logger.info(f"Env var {env_var} not set, skipping related config.")

    return watched_map


def load_repo() -> git.Repo:
    """Clone the repository if not present, otherwise pull the latest changes, and return the git.Repo object."""
    if not os.path.exists(settings.clone_dir):
        logger.info(f"Cloning repo {settings.repo_url} into {settings.clone_dir} ...")
        repo = git.Repo.clone_from(settings.repo_url, settings.clone_dir)
    else:
        repo = git.Repo(settings.clone_dir)
        logger.info(f"Pulling latest changes for repo {settings.repo_url} ...")
        repo.remotes.origin.pull()
    return repo


def config_files_changed(repo: git.Repo, previous_commit: Optional[str], watched_paths: list[str]) -> bool:
    """Check if any of the watched files have changed between the previous and current commit.

    :param repo: The git repository object.
    :type repo: git.Repo
    :param previous_commit: The previous commit hash to compare against.
    :type previous_commit: Optional[str]
    :param watched_paths: List of file paths to watch for changes.
    :type watched_paths: list[str]
    :return: True if any watched file has changed, False otherwise.
    :rtype: bool
    """
    head = repo.head.commit.hexsha
    if previous_commit is None or previous_commit != head:
        diff = repo.git.diff(f"{previous_commit}..{head}" if previous_commit else head, name_only=True).splitlines()
        logger.debug(f"Changed files between commits {previous_commit} -> {head}: {diff}")
        for watched_file in watched_paths:
            if watched_file in diff:
                logger.info(f"Detected change in watched file: {watched_file}")
                return True
    return False


def load_and_validate_configs(watched_map: dict[str, str]) -> dict[str, dict]:
    """
    Load and validate config files from absolute paths.

    :param watched_map: Dict mapping absolute file paths to ConfigMap keys.
    :return: Dict mapping file paths to loaded YAML content.
    """
    configs = {}
    for file_path in watched_map.keys():
        try:
            with open(file_path) as f:
                configs[file_path] = load_yaml(f)
            logger.debug(f"Successfully loaded config file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to load config file {file_path}: {e}")
            raise

    try:
        EODataAccessGateway()
        logger.info("EODAG configuration validation successful.")
    except Exception as e:
        logger.error(f"EODAG configuration validation failed: {e}")
        raise

    return configs


def configmap_data_changed(api: client.CoreV1Api, cm_name: str, namespace: str, key: str, new_data: str) -> bool:
    """
    Check if the data for a specific key in a Kubernetes ConfigMap has changed compared to new data.

    :param api: The Kubernetes CoreV1Api client.
    :type api: client.CoreV1Api
    :param cm_name: The name of the ConfigMap.
    :type cm_name: str
    :param namespace: The Kubernetes namespace of the ConfigMap.
    :type namespace: str
    :param key: The key within the ConfigMap to check.
    :type key: str
    :param new_data: The new data to compare against the existing ConfigMap data.
    :type new_data: str
    :return: True if the ConfigMap data has changed or does not exist, False otherwise.
    :rtype: bool
    """
    try:
        existing_cm = api.read_namespaced_config_map(cm_name, namespace)
        old_data = existing_cm.data.get(key, None)
        if old_data != new_data:
            logger.debug(f"ConfigMap '{cm_name}' key '{key}' data differs from new data.")
            return True
        else:
            logger.debug(f"ConfigMap '{cm_name}' key '{key}' data is unchanged.")
            return False
    except client.exceptions.ApiException as e:
        if e.status == 404:
            logger.debug(f"ConfigMap '{cm_name}' does not exist yet.")
            return True  # Need to create it
        else:
            logger.error(f"Error checking ConfigMap '{cm_name}': {e}")
            raise


def update_configmaps(api: client.CoreV1Api, configs: Dict[str, dict], watched_map: Dict[str, str]) -> bool:
    """Update ConfigMaps only if data changed.

    Returns True if any ConfigMap was updated or created.
    """
    any_update = False
    for git_path, content in configs.items():
        cm_key = watched_map[git_path]
        cm_name = f"{settings.configmap_name_prefix}-{cm_key.replace('/', '-').replace('.', '-')}"
        new_yaml = yaml.dump(content)
        if configmap_data_changed(api, cm_name, settings.k8s_namespace, cm_key, new_yaml):
            cm_body = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=cm_name, namespace=settings.k8s_namespace), data={cm_key: new_yaml}
            )
            try:
                api.patch_namespaced_config_map(cm_name, settings.k8s_namespace, cm_body)
                logger.info(f"ConfigMap '{cm_name}' updated with key '{cm_key}'.")
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    api.create_namespaced_config_map(settings.k8s_namespace, cm_body)
                    logger.info(f"ConfigMap '{cm_name}' created.")
                else:
                    logger.error(f"Failed to update ConfigMap '{cm_name}': {e}")
                    raise
            any_update = True
        else:
            logger.info(f"No update needed for ConfigMap '{cm_name}'.")
    return any_update


def trigger_rollout(apps_api: client.AppsV1Api):
    """
    Trigger a rollout (restart) of the specified Kubernetes deployment by updating its annotation.

    :param apps_api: The Kubernetes AppsV1Api client.
    :type apps_api: client.AppsV1Api
    :raises Exception: If the rollout trigger fails.
    """
    try:
        deployment = apps_api.read_namespaced_deployment(settings.deployment_name, settings.k8s_namespace)
        if deployment.spec.template.metadata.annotations is None:
            deployment.spec.template.metadata.annotations = {}
        import datetime

        rollout_annotation = datetime.datetime.utcnow().isoformat() + "Z"
        deployment.spec.template.metadata.annotations["kubectl.kubernetes.io/restartedAt"] = rollout_annotation
        apps_api.patch_namespaced_deployment(settings.deployment_name, settings.k8s_namespace, deployment)
        logger.info(f"Deployment '{settings.deployment_name}' rollout triggered at {rollout_annotation}.")
    except Exception as e:
        logger.error(f"Failed to trigger rollout for deployment '{settings.deployment_name}': {e}")
        raise


async def poll_for_changes():
    """Poll the git repository for configuration changes and update Kubernetes ConfigMaps and deployments as needed."""
    global last_commit_hash
    load_kube_config()
    api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    watched_map = get_watched_files_map()
    watched_paths = list(watched_map.keys())

    logger.info(f"Starting poll loop every {settings.poll_interval}s watching files: {watched_paths}")

    while True:
        try:
            repo = git.Repo(settings.clone_dir)
            if config_files_changed(repo, last_commit_hash, watched_paths):
                logger.info("Config change detected by polling. Applying changes...")
                configs = load_and_validate_configs(watched_map)
                updated = update_configmaps(api, configs, watched_map)
                if updated:
                    trigger_rollout(apps_api)
                else:
                    logger.info("No ConfigMap changes detected; rollout skipped.")
                last_commit_hash = repo.head.commit.hexsha
            else:
                logger.debug("No relevant config change detected during poll.")
        except Exception as e:
            logger.error(f"Error during polling: {e}")
        await asyncio.sleep(settings.poll_interval)


# --- Webhook handler ---
@app.post("/webhook")
async def webhook(request: Request, x_hub_signature_256: Optional[str] = Header(None)):
    """
    Handle incoming webhook POST requests to trigger configuration updates and rollouts.

    :param request: The incoming FastAPI request object containing the webhook payload.
    :type request: Request
    :param x_hub_signature_256: The HMAC SHA256 signature header for validating the webhook payload.
    :type x_hub_signature_256: Optional[str]
    :raises HTTPException: If the signature is missing or invalid, or if an error occurs during processing.
    :return: A dictionary indicating the status of the webhook processing.
    :rtype: dict
    """
    if settings.webhook_secret:
        if not x_hub_signature_256:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing signature header")
        import hashlib
        import hmac

        body = await request.body()
        sig = "sha256=" + hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, x_hub_signature_256):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    load_kube_config()
    api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    global last_commit_hash

    try:
        repo = load_repo()
        watched_map = get_watched_files_map()
        watched_paths = list(watched_map.keys())
        if config_files_changed(repo, last_commit_hash, watched_paths):
            logger.info("Config change detected via webhook. Applying changes...")
            configs = load_and_validate_configs(settings.clone_dir, watched_map)
            updated = update_configmaps(api, configs, watched_map)
            if updated:
                trigger_rollout(apps_api)
            else:
                logger.info("No ConfigMap changes detected; rollout skipped.")
            last_commit_hash = repo.head.commit.hexsha
        else:
            logger.info("Webhook received but no relevant config change detected.")
    except Exception as e:
        logger.error(f"Error processing webhook event: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing webhook") from e

    return {"status": "success"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """API init and tear-down"""
    global last_commit_hash
    repo = load_repo()
    last_commit_hash = repo.head.commit.hexsha
    logger.info(f"Initial commit hash: {last_commit_hash}")

    if settings.poll_interval != -1:
        logger.info(f"Starting polling task with interval {settings.poll_interval}s")
        asyncio.create_task(poll_for_changes())
    else:
        logger.info("Polling disabled by configuration.")
    yield
