# stac-fastapi-eodag

<p align="center">
  <img src="https://camo.githubusercontent.com/d1ceef80d0bb911c060dce8c6a6ad1a62697ee2bf7b839378a59d15bdc25337f/68747470733a2f2f656f6461672e72656164746865646f63732e696f2f656e2f6c61746573742f5f7374617469632f656f6461675f627963732e706e67" style="vertical-align: middle; max-width: 400px; max-height: 100px;" height=100 />
  <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="FastAPI" style="vertical-align: middle; max-width: 400px; max-height: 100px;" width=200 />
</p>


[EODAG](https://github.com/CS-SI/eodag) backend for [stac-fastapi](https://github.com/stac-utils/stac-fastapi), the [FastAPI](https://fastapi.tiangolo.com/) implementation of the [STAC API spec](https://github.com/radiantearth/stac-api-spec)


## Disclaimer

This project is a WIP and not ready for any production usage. Use at your own risks.

## TODO

- logging to complete (with correct thread id)
- add missing item props using custom extensions
- fix pagination on Search
- queryables
- add assets to returned items
- context extension ?
- querier / filter extension
- multiple ids item search when supported by EODAG
- unit tests

## License

stac-fastapi-eodag is licensed under Apache License v2.0.
See [LICENSE](LICENSE) file for details.
