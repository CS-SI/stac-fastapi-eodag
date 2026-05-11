FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.13 /uv /usr/local/bin/uv

RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app
RUN chown appuser /app

USER appuser

COPY --chown=appuser pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra server --extra telemetry --no-install-project

COPY --chown=appuser stac_fastapi/ stac_fastapi/
RUN uv sync --frozen --no-dev --extra server --extra telemetry

EXPOSE 8080

CMD ["/app/.venv/bin/uvicorn", "stac_fastapi.eodag.app:app", "--host", "0.0.0.0", "--port", "8080"]
