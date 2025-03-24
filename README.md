# stac-fastapi-eodag

<p align="center">
  <img src="https://eodag.readthedocs.io/en/latest/_static/eodag_bycs.png" height=80 />
  <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="FastAPI" height=100 />
</p>


[EODAG](https://github.com/CS-SI/eodag) backend for [stac-fastapi](https://github.com/stac-utils/stac-fastapi), the [FastAPI](https://fastapi.tiangolo.com/) implementation of the [STAC API spec](https://github.com/radiantearth/stac-api-spec)


## Disclaimer

This project is a WIP and not ready for any production usage. Use at your own risks.

## Run stac-fastapi-eodag locally

### Before getting started
Make sure you have the required dependencies installed:

```bash
   pip install .[server]
```

### Running the server
Once the server is properly set up, you can start it with:

```bash
   python stac_fastapi/eodag/app.py
```

By default, the EODAG HTTP server runs at port 8000.

## Run in a container

To run the server as a container:

1. Build the container image:

```bash
   docker build -t eodag-fastapi .
```

2. Run the container:

```bash
   docker run -p 8000:8000 eodag-fastapi
```

## Docker Compose
You can also run the server using Docker Compose:

```bash
docker-compose up
```

## Run in Kubernetes

You can install stac-fastapi-eodag in your Kubernetes cluster with the [Helm chart in this repository](./helm/stac-fastapi-eodag/README.md).


## Contribute

Have you spotted a typo in our documentation? Have you observed a bug while running stac-fastapi-eodag? Do you have a suggestion for a new feature?

Don't hesitate and open an issue or submit a pull request, contributions are most welcome!

For guidance on setting up a development environment and how to make a contribution to eodag, see the [contributing guidelines](./CONTRIBUTING.md).

## License

stac-fastapi-eodag is licensed under Apache License v2.0.
See [LICENSE](LICENSE) file for details.
