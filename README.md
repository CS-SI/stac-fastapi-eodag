# stac-fastapi-eodag

<p align="center">
  <img src="https://eodag.readthedocs.io/en/latest/_static/eodag_bycs.png" height=80 />
  <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="FastAPI" height=100 />
</p>

[EODAG](https://github.com/CS-SI/eodag) backend for [stac-fastapi](https://github.com/stac-utils/stac-fastapi), the [FastAPI](https://fastapi.tiangolo.com/) implementation of the [STAC API spec](https://github.com/radiantearth/stac-api-spec)

stac-fastapi-eodag combines the capabilities of EODAG and STAC FastAPI to provide a powerful, unified API for accessing Earth observation data from various providers.

## Disclaimer

⚠️ This project is a **WIP** and not ready for any production usage. Use at your own risks.

## Getting started

### Run stac-fastapi-eodag locally

#### Prerequisites
Make sure you have the required dependencies installed:

```shell
pip install .[server]
```

#### Running the server
Once the server is properly set up, you can start it with:

```shell
python stac_fastapi/eodag/app.py

# or run directly using uvicorn
# the uvicorn parameters configuration will not be applied
uvicorn stac_fastapi.eodag.app:app
```

By default, the EODAG HTTP server runs at port 8000.

### Run in a container

To run the server as a container:

1. Build the container image:

```shell
docker build -t eodag-fastapi .
```

2. Run the container:

```shell
docker run -p 8000:8000 eodag-fastapi
```

### Docker Compose

You can also run the server using Docker Compose:

```shell
docker compose up
```

NOTE: This will start a stac-fastapi-eodag container and an otel-collector container for the collection of metrics. The STAC API is available on `http://localhost:8080`, the metrics can be checked using `http://localhost:8000/metrics`.

### Run in Kubernetes

You can install stac-fastapi-eodag in your Kubernetes cluster with the [Helm chart in this repository](./helm/stac-fastapi-eodag/README.md).

## Configuration

stac-fastapi-eodag supports multiple environment variables to customize the deployment of your API.

### Uvicorn parameters

| name | description | default value |
| --- | --- | --- |
| `APP_HOST` | Bind socket to this host. Use `0.0.0.0` to make the application available from every host.| 0.0.0.0 |
| `APP_PORT` | Port from which the application is available. | 8000 |
| `RELOAD` | Enable auto-reload. **Useful for debug, should be disabled for production.** | True |
| `UVICORN_ROOT_PATH` | Used to compute the `base_url` when exposing the API on a subPath. For instance `/stac`. You should set `ROOT_PATH` (from stac-fastapi parameters) as well. **This parameter does not change the path on which the API is exposed. It only modify the links in the response body.** | "" |

The full list of available Uvicorn parameters is available from [Uvicorn settings page](https://www.uvicorn.org/settings/).

### stac-fastapi parameters

| name | description | default value |
| --- | --- | --- |
| `STAC_FASTAPI_TITLE` | Title of the API. It is displayed on the landing page. | "stac-fastapi" |
| `STAC_FASTAPI_DESCRIPTION` | Description for the API. It is displayed on the landing page. | "stac-fastapi" |
| `STAC_FASTAPI_VERSION` | It is the version number of your API instance. This is not the STAC version. It is displayed on the landing page. | 0.1 |
| `STAC_FASTAPI_LANDING_PAGE_ID` | It is a unique identifier for the landing page. It is displayed on the landing page. | "stac-fastapi" |
| `ENABLE_RESPONSE_MODELS` | Turn on response validation. | False |
| `OPENAPI_URL` | Path for the OpenAPI definition of the API. | "/api" |
| `DOCS_URL` | Path for the Swagger UI of the API. | "/api.html" |
| `ROOT_PATH` | Used to compute the `base_url` when exposing the API on a subPath. For instance `/stac`. You should set `UVICORN_ROOT_PATH` (from Uvicorn parameters) as well. **This parameter does not change the path on which the API is exposed. It only modify the links in the response body.**  | "" |

Reach to [stac-fastapi documentation](https://stac-utils.github.io/stac-fastapi/) for exhaustive documentation on stac-fastapi.

### stac-fastapi-eodag parameters

| name | description | default value |
| --- | --- | --- |
| `DEBUG` | When set to `True`, set the EODAG logging level to `3`. Otherwise, set EODAG logging level to `2`. | False |
| `KEEP_ORIGIN_URL` | Keep origin as alternate URL when data-download extension is enabled. | False |
| `ORIGIN_URL_BLACKLIST` | Hide from clients items assets' origin URLs starting with URLs from the list. A string of comma separated values is expected. | "" |
| `COUNT` | Whether to run a query with a count request or not. | False |
| `FETCH_PROVIDERS` | Fetch additional collections from all EODAG providers. | False |
| `AUTO_ORDER_WHITELIST` | List of providers for which the order should be done at the same time as the download. | ["wekeo_main"] |
| `DOWNLOAD_BASE_URL` | Useful to expose asset download URL in a separate domain name. | "" |

### OpenTelemetry parameters

| name | description | default value |
| --- | --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Target url to which the exporter sends the metrics. | "" |
| `OTEL_METRIC_EXPORT_INTERVAL` | Time interval (in milliseconds) between the start of two export attempts. | 60000 |
| `OTEL_EXPORTER_OTLP_TIMEOUT` |  Timeout value for all outgoing data (traces, metrics, and logs) in milliseconds. | 10000 |

To start an otel-collector container and to connect it to an instance of STAC API the following commands can be used:

```shell
pip install .[server,telemetry]
docker run -p 4318:4318 -p 8000:8000 \
    -v ./config/otelcol_config.yml:/etc/otel-collector-config.yaml \
    otel/opentelemetry-collector:latest \
    --config=/etc/otel-collector-config.yaml
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318/"
export OTEL_METRIC_EXPORT_INTERVAL="5000"  # shorter export interval for testing
export APP_PORT=8080  # change app port because otel-collector uses 8000
python stac_fastapi/eodag/app.py
```

### EODAG parameters

EODAG configuration parameters are available from [EODAG documentation](https://eodag.readthedocs.io/en/stable/getting_started_guide/configure.html).

## Contribute

Have you spotted a typo in our documentation? Have you observed a bug while running stac-fastapi-eodag? Do you have a suggestion for a new feature?

Don't hesitate and open an issue or submit a pull request, contributions are most welcome!

For guidance on setting up a development environment and how to make a contribution to eodag, see the [contributing guidelines](./CONTRIBUTING.md).

## Acknowledgments

We would like to express our gratitude to the maintainers and contributors of the following projects which have been instrumental in the development of this project:

- [stac-fastapi](https://github.com/stac-utils/stac-fastapi): Thanks to the stac-fastapi team for their implementation of the STAC API spec.
- [FastAPI](https://github.com/FastAPI/FastAPI): Thanks to the FastAPI team for providing a modern, fast (high-performance) web framework for building APIs.


## License

stac-fastapi-eodag is licensed under Apache License v2.0.
See [LICENSE](LICENSE) file for details.
