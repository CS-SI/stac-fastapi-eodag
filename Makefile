##@ Project's Makefile, with utility commands for the project development lifecycle.

PYTHON=python3
PIP=$(PYTHON) -mpip
TOX=$(PYTHON) -mtox
PRE_COMMIT=$(PYTHON) -mpre_commit

.PHONY: default help release build install install-dev
.PHONY: shell test lint lint-watch docs docs-live security
.PHONY: clean report serve pipeline pre-commit

# ======================================================= #

default: help

release: ## Bump version, create tag and update CHANGELOG.
	@$(PYTHON) -mcommitizen bump --yes --changelog

build: ## Build wheel and tar.gz in 'dist/'.
	@$(PYTHON) -mbuild

install: ## Install in the current python env.
	@$(PIP) install .

install-dev: ## Install in editable mode inside the current python env with dev dependencies.
	@$(PIP) install -e .[dev]

shell: ## Open Python shell.
	@$(PYTHON) -mbpython

test: ## Invoke pytest to run automated tests.
	@$(TOX)

lint: ## Lint python source code.
	@$(PRE_COMMIT) run --files $(shell find src tests -name "*.py")

lint-watch: ## Run ruff linter with --watch (ruff needs to be installed)
	@$(PYTHON) -mruff check src --fix --watch

report: ## Start http server to serve the test report and coverage.
	@printf "Test report: http://localhost:9000\n"
	@printf "Coverage report: http://localhost:9000/coverage\n"
	@$(PYTHON) -mhttp.server -b 0.0.0.0 -d tests-reports 9000 > /dev/null

clean: ## Clean temporary files, like python __pycache__, dist build, tests reports.
	@find src tests -regex "^.*\(__pycache__\|\.py[co]\)$$" -delete
	@rm -rf dist tests-reports .coverage* .*_cache

pipeline: security lint test build ## Run security, lint, test, build.

pre-commit: ## Run all pre-commit hooks.
	@$(PRE_COMMIT) run --all-files
	@$(PRE_COMMIT) run --hook-stage push --all-files

# ======================================================= #

IMAGE_VERSION?="latest"
IMAGE_NAME=$(shell basename $(CURDIR))
IMAGE_PREFIX="ghcr.io/cs-si/stac-fastapi-eodag"

docker: docker-rm docker-build docker-run  ## re-create Docker image and container

docker-build: ## Build the Docker image shipping application
	@echo "[INFO - $$(date +'%d/%m/%Y %H:%M:%S')] Building ${IMAGE_NAME}:${IMAGE_VERSION} Docker image..."
	@docker build \
		--tag ${IMAGE_NAME}:${IMAGE_VERSION} \
		.

docker-rm: ## Delete Docker container
	@echo "[INFO - $$(date +'%d/%m/%Y %H:%M:%S')] Removing ${IMAGE_NAME}-${IMAGE_VERSION} Docker image if exists."
	@-docker rm ${IMAGE_NAME}-${IMAGE_VERSION} -f 2>/dev/null
	@echo "[INFO - $$(date +'%d/%m/%Y %H:%M:%S')] Docker image ${IMAGE_NAME}-${IMAGE_VERSION} successfully removed if existing"

docker-run: ## Run Docker container for testing purposes
	@echo "[INFO - $$(date +'%d/%m/%Y %H:%M:%S')] Running container from image ${IMAGE_NAME}:${IMAGE_VERSION}..."
	@docker run \
		--detach \
		--name ${IMAGE_NAME}-${IMAGE_VERSION} \
		${IMAGE_NAME}:${IMAGE_VERSION}
	@echo "[INFO - $$(date +'%d/%m/%Y %H:%M:%S')] Container starting..."

docker-logs: ## print Docker container log
	@docker logs -f ${IMAGE_NAME}-${IMAGE_VERSION}

docker-start: ## start Docker container
	@echo "[INFO - $$(date +'%d/%m/%Y %H:%M:%S')] Container starting..."
	@docker start ${IMAGE_NAME}-${IMAGE_VERSION}

docker-stop: ## stop Docker container
	@echo "[INFO - $$(date +'%d/%m/%Y %H:%M:%S')] Container stopping..."
	@docker stop ${IMAGE_NAME}-${IMAGE_VERSION}

docker-tag:
	@docker tag \
		${IMAGE_NAME}:${IMAGE_VERSION} \
		${IMAGE_PREFIX}/${IMAGE_NAME}:${IMAGE_VERSION}

docker-push:
	@docker push \
		${IMAGE_PREFIX}/${IMAGE_NAME}:${IMAGE_VERSION}

# ======================================================= #

HELP_COLUMN=11
help: ## Show this help.
	@printf "\033[1m################\n#     Help     #\n################\033[0m\n"
	@awk 'BEGIN {FS = ":.*##@"; printf "\n"} /^##@/ { printf "%s\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n\n  make \033[36m<target>\033[0m\n\n"} /^[$$()% a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-$(HELP_COLUMN)s\033[0m %s\n", $$1, $$2 } ' $(MAKEFILE_LIST)
	@printf "\n"
