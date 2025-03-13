# stac-fastapi-eodag

<p align="center">
  <img src="https://eodag.readthedocs.io/en/latest/_static/eodag_bycs.png" height=80 />
  <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="FastAPI" height=100 />
</p>


[EODAG](https://github.com/CS-SI/eodag) backend for [stac-fastapi](https://github.com/stac-utils/stac-fastapi), the [FastAPI](https://fastapi.tiangolo.com/) implementation of the [STAC API spec](https://github.com/radiantearth/stac-api-spec)


## Disclaimer

This project is a WIP and not ready for any production usage. Use at your own risks.


## Before getting started
Make sure you have the required dependencies installed:

.. code-block:: bash

   pip install .[server]

## Running the server
Once the server is properly set up, you can start it with:

.. code-block:: bash

   python stac_fastapi/eodag/app.py

By default, the EODAG HTTP server runs at port 8000.

## Docker
To run the server using Docker:

1. Build the Docker image:

.. code-block:: bash

   docker build -t eodag-fastapi .

2. Run the container:

.. code-block:: bash

   docker run -p 8000:8000 eodag-fastapi

## Docker Compose
You can also run the server using Docker Compose:

.. code-block:: bash
docker-compose up

## Code Quality and Pre-commit
If you modify the code, it's important to run the pre-commit to ensure code quality and consistency. Pre-commit helps automatically check and fix issues like code formatting, linting errors, and other potential problems before committing changes to the repository.

### Installing pre-commit
Make sure to have `pre-commit` installed. If you haven't already, you can install it by running:

.. code-block:: bash

   pip install pre-commit

### Running pre-commit
If you want to  run the pre-commit on all files (for example, if you've made changes to files that haven't been staged yet), you can run:

.. code-block:: bash

   pre-commit run --all-files

This command will check all the files in the repository and apply any necessary fixes, ensuring that your code adheres to the specified guidelines.


## License

stac-fastapi-eodag is licensed under Apache License v2.0.
See [LICENSE](LICENSE) file for details.
