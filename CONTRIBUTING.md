# Contribute

Thank you for considering contributing to stac-fastapi-eodag!

- [Report issues](#report-issues)
- [Submit patches](#submit-patches)
- [Contribute to the Helm chart](#contribute-to-the-helm-chart)

## Report issues

[Issue tracker](https://github.com/CS-SI/stac-fastapi-eodag/issues)

Please check that a similar issue does not already exist and include the following information in your post:

- Describe what you expected to happen.
- If possible, include a [minimal reproducible example](https://stackoverflow.com/help/minimal-reproducible-example) to help us identify the issue. This also helps check that the issue is not with your own code.
- Describe what actually happened. Include the full traceback if there was an exception.
- List your Python and eodag versions. If possible, check if this issue is already fixed in the latest releases or the latest code in the repository.

## Submit patches

If you intend to contribute to eodag source code:

### 1. Get the source code and install dependencies

```bash
git clone https://github.com/CS-SI/stac-fastapi-eodag.git
cd stac-fastapi-eodag
python -m pip install -e .[dev,server]
pre-commit install
```

We use `pre-commit` to run a suite of linters, formatters and pre-commit hooks to ensure the code base is homogeneously formatted and easier to read.

## Contribute to the Helm chart

stac-fastapi-eodag uses [Helm](https://helm.sh) to package the application for [Kubernetes](http://kubernetes.io).

The parameters section is automatically generated from comments left in the `values.yaml`.
Run the following command to update the chart `README.md` after modifying the values file.

```shell
npm install @bitnami/readme-generator-for-helm
export PATH="node_modules/.bin":$PATH
readme-generator --values "./helm/stac-fastapi-eodag/values.yaml" --readme "./helm/stac-fastapi-eodag/README.md" --schema "/tmp/schema.json"
```
