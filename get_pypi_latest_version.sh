#!/usr/bin/env bash

curl https://pypi.org/pypi/stac-fastapi-eodag/json | python -c "import sys, json; print(json.load(sys.stdin)['info']['version']);"
