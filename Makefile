.PHONY: install-deps test lint run helm-docs

install-deps:
	uv sync --extra dev --extra server --extra telemetry
	uv run pre-commit install

test:
	uv run pytest

lint:
	uv run pre-commit run --all-files
	uv run mypy stac_fastapi

run:
	uv run uvicorn stac_fastapi.eodag.app:app --host 0.0.0.0 --port 8080 --reload

helm-docs:
	docker run --rm --volume "$(PWD):/helm-docs" -u $(shell id -u) jnorwood/helm-docs:latest --chart-search-root=helm
