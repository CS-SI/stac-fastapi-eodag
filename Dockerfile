FROM python:3.12

# start from root
WORKDIR /stac-fastapi-eodag

# copy necessary files
COPY pyproject.toml pyproject.toml
COPY stac_fastapi/eodag stac_fastapi/eodag

# install server
RUN python -m pip install .[server]

ENTRYPOINT ["/bin/bash", "-c", "python stac_fastapi/eodag/app.py"] 
