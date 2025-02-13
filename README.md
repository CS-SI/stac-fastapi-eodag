# stac-fastapi-eodag

<p align="center">
  <img src="https://eodag.readthedocs.io/en/latest/_static/eodag_bycs.png" height=80 />
  <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="FastAPI" height=100 />
</p>


[EODAG](https://github.com/CS-SI/eodag) backend for [stac-fastapi](https://github.com/stac-utils/stac-fastapi), the [FastAPI](https://fastapi.tiangolo.com/) implementation of the [STAC API spec](https://github.com/radiantearth/stac-api-spec)


## Disclaimer

This project is a WIP and not ready for any production usage. Use at your own risks.

## TODO

- logging to complete (with correct thread id)
- add missing item props using custom extensions
- context extension ?
- querier / filter extension, for queryables as well ?
- multiple ids item search when supported by EODAG
- unit tests
- download extension
- multi provider handling. Check the federation openeo extension ?
- caching

## License

stac-fastapi-eodag is licensed under Apache License v2.0.
See [LICENSE](LICENSE) file for details.
