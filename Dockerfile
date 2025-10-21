ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

COPY . /app

RUN python -m pip install  --no-cache-dir .[server,telemetry]

RUN adduser --disabled-password --gecos '' appuser

USER appuser

EXPOSE 8080

CMD ["uvicorn", "stac_fastapi.eodag.app:app", "--host", "0.0.0.0", "--port", "8080"]
