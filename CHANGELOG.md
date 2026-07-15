# CHANGELOG

<!-- version list -->

## v0.4.0 (2026-07-15)

### Bug Fixes

- Asset type property and item extensions
  ([#73](https://github.com/CS-SI/stac-fastapi-eodag/pull/73),
  [`078134a`](https://github.com/CS-SI/stac-fastapi-eodag/commit/078134a4816f823068966a7926c71502609bbc9d))

- Collections instruments as list ([#75](https://github.com/CS-SI/stac-fastapi-eodag/pull/75),
  [`35903b5`](https://github.com/CS-SI/stac-fastapi-eodag/commit/35903b5a120ebdb1f5bd1613798a1c7f2e1961ad))

- Format methods property ([#81](https://github.com/CS-SI/stac-fastapi-eodag/pull/81),
  [`26108ac`](https://github.com/CS-SI/stac-fastapi-eodag/commit/26108aca04b39cfaaf233a3e53a4bf219a374e54))

- Milliseconds precision in dates and tests update
  ([#90](https://github.com/CS-SI/stac-fastapi-eodag/pull/90),
  [`afb8fcb`](https://github.com/CS-SI/stac-fastapi-eodag/commit/afb8fcb85f9add2a3f0e34bfef5b794ca96f255a))

- No retrieve body for wekeo_main ([#71](https://github.com/CS-SI/stac-fastapi-eodag/pull/71),
  [`f9f6e60`](https://github.com/CS-SI/stac-fastapi-eodag/commit/f9f6e6039242b092113c4aeb8ce7bc1a908838f3))

- Pagination internal FDP providers ([#79](https://github.com/CS-SI/stac-fastapi-eodag/pull/79),
  [`2c4ae12`](https://github.com/CS-SI/stac-fastapi-eodag/commit/2c4ae127176e2ed4cd85177aab00fd82d91d383f))

- Queryables with same serialization and validation alias
  ([#82](https://github.com/CS-SI/stac-fastapi-eodag/pull/82),
  [`767e89b`](https://github.com/CS-SI/stac-fastapi-eodag/commit/767e89bd4f002d65c6452c403c1b377c7f8d9d0d))

- Remove numberMatched when count is False
  ([#83](https://github.com/CS-SI/stac-fastapi-eodag/pull/83),
  [`8be05e4`](https://github.com/CS-SI/stac-fastapi-eodag/commit/8be05e4a23e511d25bae216158deaf9b1b45b8b3))

- Remove page parameter leftovers ([#78](https://github.com/CS-SI/stac-fastapi-eodag/pull/78),
  [`d395992`](https://github.com/CS-SI/stac-fastapi-eodag/commit/d395992fff7b4d6359b3c1027881426ef070f2fe))

- Replace deprecated ORJSONResponse with JSONResponse
  ([`74c5c99`](https://github.com/CS-SI/stac-fastapi-eodag/commit/74c5c99af4e84c61b67472a5766fcd42eaa46d60))

- Resolve SonarQube issues ([#112](https://github.com/CS-SI/stac-fastapi-eodag/pull/112),
  [`b465f43`](https://github.com/CS-SI/stac-fastapi-eodag/commit/b465f4386a8831678a35f9856def1bc67b153807))

- Run eodag using asyncio.to_thread ([#97](https://github.com/CS-SI/stac-fastapi-eodag/pull/97),
  [`2970a69`](https://github.com/CS-SI/stac-fastapi-eodag/commit/2970a698342c54df94fc17fc1570f387ec58dc23))

- Unpin starlette and use official CORSMiddleware
  ([#95](https://github.com/CS-SI/stac-fastapi-eodag/pull/95),
  [`9ce6fe4`](https://github.com/CS-SI/stac-fastapi-eodag/commit/9ce6fe48748c26231d33438cbad38617f195bba4))

- Update collection attributes from external collection
  ([#103](https://github.com/CS-SI/stac-fastapi-eodag/pull/103),
  [`2698f0a`](https://github.com/CS-SI/stac-fastapi-eodag/commit/2698f0a97b3d52d9bc3b75f64f1ba46efaf0bf15))

- Use a stable version of eodag as dep
  ([#109](https://github.com/CS-SI/stac-fastapi-eodag/pull/109),
  [`8b751a8`](https://github.com/CS-SI/stac-fastapi-eodag/commit/8b751a895170d7b73fa8343c8778f413ea74924c))

- Use dict for external collection links
  ([#85](https://github.com/CS-SI/stac-fastapi-eodag/pull/85),
  [`d299420`](https://github.com/CS-SI/stac-fastapi-eodag/commit/d299420bc9f4945321f8be0badad13fa6b991f90))

- **queryables**: Adapt parameters' value before passing them to EODAG
  ([#93](https://github.com/CS-SI/stac-fastapi-eodag/pull/93),
  [`e458c69`](https://github.com/CS-SI/stac-fastapi-eodag/commit/e458c6923ddec9813a15d0f53597f6014c0c9cae))

### Build System

- Add git for image build ([#91](https://github.com/CS-SI/stac-fastapi-eodag/pull/91),
  [`4bd3978`](https://github.com/CS-SI/stac-fastapi-eodag/commit/4bd39785ce9f2acdd2840ebcdd5077f319b189df))

- Bump base Python image to 3.14
  ([`1289ac4`](https://github.com/CS-SI/stac-fastapi-eodag/commit/1289ac404a92360dfb8a9fe7c388310cd46a87d7))

- Only build on releases ([#92](https://github.com/CS-SI/stac-fastapi-eodag/pull/92),
  [`2f24c2d`](https://github.com/CS-SI/stac-fastapi-eodag/commit/2f24c2d2f5771bb3388d90d0d0c7d9098d2844c0))

- Rewrite Dockerfile using uv with layer cache optimization
  ([`fdbb60c`](https://github.com/CS-SI/stac-fastapi-eodag/commit/fdbb60cb1fe316f03ad954a8280ba3d7c01eb64a))

- Temporarily pin starlette max version ([#94](https://github.com/CS-SI/stac-fastapi-eodag/pull/94),
  [`6d538d1`](https://github.com/CS-SI/stac-fastapi-eodag/commit/6d538d1f6aeebedf552a9e8cfa17f8bc80813925))

- **deps**: Bump brace-expansion from 1.1.11 to 1.1.12
  ([#74](https://github.com/CS-SI/stac-fastapi-eodag/pull/74),
  [`28682e8`](https://github.com/CS-SI/stac-fastapi-eodag/commit/28682e81838a4ac4464a66856dbb3662bba63cdf))

### Chores

- Fix mypy arg-type errors for get_metadata_path_value in data_download
  ([#124](https://github.com/CS-SI/stac-fastapi-eodag/pull/124),
  [`d02dedc`](https://github.com/CS-SI/stac-fastapi-eodag/commit/d02dedc286abf098bc9c22e53dd3873c3015d49f))

- Replace bitnami readme-generator with helm-docs
  ([#113](https://github.com/CS-SI/stac-fastapi-eodag/pull/113),
  [`a06e930`](https://github.com/CS-SI/stac-fastapi-eodag/commit/a06e9301d56b8247cb109b0ff0e3a74d79922542))

- Simplify release automation ([#120](https://github.com/CS-SI/stac-fastapi-eodag/pull/120),
  [`eca4834`](https://github.com/CS-SI/stac-fastapi-eodag/commit/eca4834ac0d9b99efaad4a298c3214e38c7863d4))

- Track uv.lock for reproducible builds
  ([`73ac4f7`](https://github.com/CS-SI/stac-fastapi-eodag/commit/73ac4f739c359b6651fcfe18500a95894e3b01a8))

- Update dependencies ([#126](https://github.com/CS-SI/stac-fastapi-eodag/pull/126),
  [`cb93106`](https://github.com/CS-SI/stac-fastapi-eodag/commit/cb931066834a40a852a82f0284c728b8ac4a7581))

### Continuous Integration

- Fix and improve container image publishing workflow
  ([`d41a839`](https://github.com/CS-SI/stac-fastapi-eodag/commit/d41a83920f20adfeef426d891c9eb217180ebd0f))

- Fix semantic release build command ([#125](https://github.com/CS-SI/stac-fastapi-eodag/pull/125),
  [`8243e66`](https://github.com/CS-SI/stac-fastapi-eodag/commit/8243e66bce5fa66f4c6ea7a634f6794725305457))

- Trigger helm chart release on version tags only
  ([`9af1579`](https://github.com/CS-SI/stac-fastapi-eodag/commit/9af1579c572f8d0e7d3bcfe1c2585d3abadfe374))

- Upgrade GitHub Actions versions and add SonarQube job
  ([`14bbf09`](https://github.com/CS-SI/stac-fastapi-eodag/commit/14bbf09d3f2484f4bdb593bebfbf10a9b4e11517))

### Documentation

- Add SonarCloud quality gate and DeepWiki badges to README
  ([`69c84da`](https://github.com/CS-SI/stac-fastapi-eodag/commit/69c84da3b2dd43a2f6a239ceb2ac4483946a0eb6))

- Add usage example to filter collections by provider
  ([#123](https://github.com/CS-SI/stac-fastapi-eodag/pull/123),
  [`cd8db7a`](https://github.com/CS-SI/stac-fastapi-eodag/commit/cd8db7a6e4a386e125a12ec1feb741d5a2b27dc7))

- Update CONTRIBUTING and add Makefile for uv-based workflow
  ([`61e768c`](https://github.com/CS-SI/stac-fastapi-eodag/commit/61e768c74f71829d030381526c626c7674b717b9))

### Features

- Add an explicit error for json in the filter for get request
  ([#115](https://github.com/CS-SI/stac-fastapi-eodag/pull/115),
  [`7896507`](https://github.com/CS-SI/stac-fastapi-eodag/commit/78965071d8939bf4d4a3d6a2e37484f3297d96cc))

- Add filter extension for items_collection
  ([#77](https://github.com/CS-SI/stac-fastapi-eodag/pull/77),
  [`1157af8`](https://github.com/CS-SI/stac-fastapi-eodag/commit/1157af8d3374eadc9c5425a2ef281a066a53d0d4))

- Add label extensions ([#76](https://github.com/CS-SI/stac-fastapi-eodag/pull/76),
  [`c619501`](https://github.com/CS-SI/stac-fastapi-eodag/commit/c6195010cbef375a4c3c02f4091ea507babcc42c))

- Pagination token ([#34](https://github.com/CS-SI/stac-fastapi-eodag/pull/34),
  [`2381bbd`](https://github.com/CS-SI/stac-fastapi-eodag/commit/2381bbdf534244aeb2f49ec1a9a09238dfa700ac))

- Remove downloadlink for parquet type asset
  ([#106](https://github.com/CS-SI/stac-fastapi-eodag/pull/106),
  [`fd74b61`](https://github.com/CS-SI/stac-fastapi-eodag/commit/fd74b611ff6d8ebcee0f16e20eed32ae55b5e9cf))

### Refactoring

- Adapt code to collection and provider object
  ([#80](https://github.com/CS-SI/stac-fastapi-eodag/pull/80),
  [`d69369b`](https://github.com/CS-SI/stac-fastapi-eodag/commit/d69369b83d9cf5e99b602345bc6f745bbc479855))

- Adapt to change of stream download in eodag
  ([#100](https://github.com/CS-SI/stac-fastapi-eodag/pull/100),
  [`6e32d83`](https://github.com/CS-SI/stac-fastapi-eodag/commit/6e32d83f63e9a567fa0426e918945a3534ad9017))

- Optimise adding providers to collection
  ([#88](https://github.com/CS-SI/stac-fastapi-eodag/pull/88),
  [`8a0223a`](https://github.com/CS-SI/stac-fastapi-eodag/commit/8a0223ab6c2fba0f9f40047e72190d1712029711))

- Quotas errors and query extension syntax handling
  ([#104](https://github.com/CS-SI/stac-fastapi-eodag/pull/104),
  [`5a6dc68`](https://github.com/CS-SI/stac-fastapi-eodag/commit/5a6dc6866893779be1362ec7402778ce3316c2da))

- Remove peps provider ([#102](https://github.com/CS-SI/stac-fastapi-eodag/pull/102),
  [`b73a3b0`](https://github.com/CS-SI/stac-fastapi-eodag/commit/b73a3b0e74acba4be953588dd97e8a2a9a78f2fd))

- Remove STAC metadata handling + adaptations for STAC 1.1.0
  ([#99](https://github.com/CS-SI/stac-fastapi-eodag/pull/99),
  [`0eaef24`](https://github.com/CS-SI/stac-fastapi-eodag/commit/0eaef2468a056fbab48511ed4328518f467bb5ec))

- STAC filters available in EODAG ([#86](https://github.com/CS-SI/stac-fastapi-eodag/pull/86),
  [`780c7fd`](https://github.com/CS-SI/stac-fastapi-eodag/commit/780c7fde626889b5bb7901c15f945a0839d72840))


## v0.3.0 (2026-07-15)

### Chores

- **deploy**: Update chart version
  ([`2a668d1`](https://github.com/CS-SI/stac-fastapi-eodag/commit/2a668d16e561adcd3c7f55ffe2919dc759a22f8b))

### Features

- Validate search and order requests ([#56](https://github.com/CS-SI/stac-fastapi-eodag/pull/56),
  [`d456bb1`](https://github.com/CS-SI/stac-fastapi-eodag/commit/d456bb19d73af1d6e836f114540deb290554508a))

### Refactoring

- Adaptations to align with v4 of eodag ([#68](https://github.com/CS-SI/stac-fastapi-eodag/pull/68),
  [`ec200f5`](https://github.com/CS-SI/stac-fastapi-eodag/commit/ec200f5bcfa9f93e5265edca8c4592bb29b0b1e4))

### Testing

- Add `{posargs}` to `pytest` invocation
  ([#58](https://github.com/CS-SI/stac-fastapi-eodag/pull/58),
  [`7f6c14a`](https://github.com/CS-SI/stac-fastapi-eodag/commit/7f6c14afbba1e784c558c237f1aaccf9797e9890))


## v0.2.0 (2025-10-27)

### Bug Fixes

- Avoid none in instrument property ([#18](https://github.com/CS-SI/stac-fastapi-eodag/pull/18),
  [`2078767`](https://github.com/CS-SI/stac-fastapi-eodag/commit/20787675f6de66049ea30f7920e20cf7385e8e70))

- Empty body ([#15](https://github.com/CS-SI/stac-fastapi-eodag/pull/15),
  [`f9cbca9`](https://github.com/CS-SI/stac-fastapi-eodag/commit/f9cbca96f1c58743f2c017b85291a896823fdc7d))

- Fixed free-text search ([#48](https://github.com/CS-SI/stac-fastapi-eodag/pull/48),
  [`ace2899`](https://github.com/CS-SI/stac-fastapi-eodag/commit/ace289978c2396b60e5b96346464a469efbcf142))

- Make datetime filter work again on /collections
  ([#46](https://github.com/CS-SI/stac-fastapi-eodag/pull/46),
  [`a9d2192`](https://github.com/CS-SI/stac-fastapi-eodag/commit/a9d21929e5fe0c3b441604c1139b299019df38cc))

- Properly handle port with forwarded header
  ([#17](https://github.com/CS-SI/stac-fastapi-eodag/pull/17),
  [`cdb6b71`](https://github.com/CS-SI/stac-fastapi-eodag/commit/cdb6b71a1ff53d9bc12071f397e3427fc9ed321c))

- Remove providers in items and collections
  ([#6](https://github.com/CS-SI/stac-fastapi-eodag/pull/6),
  [`72ab97c`](https://github.com/CS-SI/stac-fastapi-eodag/commit/72ab97c7864e98602a74a1d3f31723ab17631bf1))

- Set server logging ([#36](https://github.com/CS-SI/stac-fastapi-eodag/pull/36),
  [`86d00ff`](https://github.com/CS-SI/stac-fastapi-eodag/commit/86d00ff392f19c4ec68363f332df7262059b8219))

- Set wekeo_main products storageTier to online
  ([#29](https://github.com/CS-SI/stac-fastapi-eodag/pull/29),
  [`e013217`](https://github.com/CS-SI/stac-fastapi-eodag/commit/e0132171ca132dd50f55d4c1b479731dfc2d495f))

- Wekeo_main order/download ([#25](https://github.com/CS-SI/stac-fastapi-eodag/pull/25),
  [`701c9e6`](https://github.com/CS-SI/stac-fastapi-eodag/commit/701c9e6dd33d5e9002000a6f110918e02fd73079))

- **collections**: Make pagination optional
  ([#35](https://github.com/CS-SI/stac-fastapi-eodag/pull/35),
  [`bcd81f1`](https://github.com/CS-SI/stac-fastapi-eodag/commit/bcd81f19bf08f4efca53de6605afde2de83296a3))

- **logs**: Debug only our logs ([#39](https://github.com/CS-SI/stac-fastapi-eodag/pull/39),
  [`c14c86b`](https://github.com/CS-SI/stac-fastapi-eodag/commit/c14c86b88768425bf96e65a6253fc01f97ce65f8))

- **queryables**: Properly set $id ([#40](https://github.com/CS-SI/stac-fastapi-eodag/pull/40),
  [`086060e`](https://github.com/CS-SI/stac-fastapi-eodag/commit/086060e0234811e7ab507f78daa33693861ebbc5))

### Build System

- Add env var for otel collector in docker compose
  ([#16](https://github.com/CS-SI/stac-fastapi-eodag/pull/16),
  [`770e47a`](https://github.com/CS-SI/stac-fastapi-eodag/commit/770e47a2980472bf6d2b13fc42e08583e5556ee3))

- Add github workflows ([#2](https://github.com/CS-SI/stac-fastapi-eodag/pull/2),
  [`d77e9f7`](https://github.com/CS-SI/stac-fastapi-eodag/commit/d77e9f752620b6ed105fd049522fe396dba6e117))

- Remove git repos from dependencies ([#33](https://github.com/CS-SI/stac-fastapi-eodag/pull/33),
  [`4a126b9`](https://github.com/CS-SI/stac-fastapi-eodag/commit/4a126b9b2b221cbc4d15a36c9d610c8b169c2248))

- **container**: Reduce image size ([#60](https://github.com/CS-SI/stac-fastapi-eodag/pull/60),
  [`e9acefb`](https://github.com/CS-SI/stac-fastapi-eodag/commit/e9acefb0680227c1f70643625c314b727d420aec))

### Chores

- Add helm chart releaser action ([#65](https://github.com/CS-SI/stac-fastapi-eodag/pull/65),
  [`ab3a453`](https://github.com/CS-SI/stac-fastapi-eodag/commit/ab3a453b93aa8c948926f12a9697cd45adf2b38c))

- Prepare for release 0.2.0 ([#66](https://github.com/CS-SI/stac-fastapi-eodag/pull/66),
  [`dd62021`](https://github.com/CS-SI/stac-fastapi-eodag/commit/dd62021c1ba62c04037dcb2221abb1eb0422d547))

- Release chart version 0.1.0
  ([`ed2dde4`](https://github.com/CS-SI/stac-fastapi-eodag/commit/ed2dde4ed137b4721ac4756f317290aae3b5bc69))

- **helm**: Add hpa, terminationGracePeriodSeconds, deployment annotations
  ([#53](https://github.com/CS-SI/stac-fastapi-eodag/pull/53),
  [`4606e49`](https://github.com/CS-SI/stac-fastapi-eodag/commit/4606e49d91b1ead1254dd68615f4ca6ea8f8ae86))

- **helm**: Improve chart description
  ([`c541296`](https://github.com/CS-SI/stac-fastapi-eodag/commit/c5412969aa46e0df633b724dd8b061da09a1a038))

### Continuous Integration

- Build container images on releases
  ([`9d0d154`](https://github.com/CS-SI/stac-fastapi-eodag/commit/9d0d1549f8e9d726a61c35be54ef6e53baba7252))

- Fix typo in extracting metadata ([#64](https://github.com/CS-SI/stac-fastapi-eodag/pull/64),
  [`53bc3d0`](https://github.com/CS-SI/stac-fastapi-eodag/commit/53bc3d070f0e6c020035fb9c016cd48a11fa0b62))

- Fix typo with uv ([#55](https://github.com/CS-SI/stac-fastapi-eodag/pull/55),
  [`d8ac23c`](https://github.com/CS-SI/stac-fastapi-eodag/commit/d8ac23c12e98a54b9af7967ca39aba20ace67644))

- Lint pr title
  ([`398addb`](https://github.com/CS-SI/stac-fastapi-eodag/commit/398addb0eebb14f5dc3df080cc9ce7d2fddefccc))

- Properly open pyproject ([#63](https://github.com/CS-SI/stac-fastapi-eodag/pull/63),
  [`a4c8993`](https://github.com/CS-SI/stac-fastapi-eodag/commit/a4c8993f820feac69809fdf48e9a35da7e7e4f09))

- Run pip install in venv ([#62](https://github.com/CS-SI/stac-fastapi-eodag/pull/62),
  [`f14e265`](https://github.com/CS-SI/stac-fastapi-eodag/commit/f14e2651d4c425b803d2ce3402824348ba10bb37))

- Set proper secret for lint pr job ([#52](https://github.com/CS-SI/stac-fastapi-eodag/pull/52),
  [`e9da406`](https://github.com/CS-SI/stac-fastapi-eodag/commit/e9da40690d6f3ff5f237e2dfb8240038f5f9c039))

- **package**: Add labels to container image
  ([#54](https://github.com/CS-SI/stac-fastapi-eodag/pull/54),
  [`8389893`](https://github.com/CS-SI/stac-fastapi-eodag/commit/8389893b500fc26683f0804ef0f0f156efcaf7d7))

### Documentation

- Update README.md
  ([`7a1f933`](https://github.com/CS-SI/stac-fastapi-eodag/commit/7a1f933d424f89ed0991338ccccaac0d60b07c9e))

### Features

- Implement sortby for /items ([#28](https://github.com/CS-SI/stac-fastapi-eodag/pull/28),
  [`627ab00`](https://github.com/CS-SI/stac-fastapi-eodag/commit/627ab001040f0fcba504c0b7e9379bae880faebf))

- Paginate collection ([#26](https://github.com/CS-SI/stac-fastapi-eodag/pull/26),
  [`288c3c6`](https://github.com/CS-SI/stac-fastapi-eodag/commit/288c3c628d9101d6a8d7c859c4f06c47bb189640))

- Redirect to pre-signed url ([#42](https://github.com/CS-SI/stac-fastapi-eodag/pull/42),
  [`e1ba8b5`](https://github.com/CS-SI/stac-fastapi-eodag/commit/e1ba8b5b97503f586668974264504b6f6c687690))

- **core**: Set count search parameter to its value in settings
  ([#31](https://github.com/CS-SI/stac-fastapi-eodag/pull/31),
  [`5d79ce2`](https://github.com/CS-SI/stac-fastapi-eodag/commit/5d79ce2226b3d72164e1de672702c0fe615969c9))

### Refactoring

- Download link type ([#32](https://github.com/CS-SI/stac-fastapi-eodag/pull/32),
  [`c47bceb`](https://github.com/CS-SI/stac-fastapi-eodag/commit/c47bceba84b37fd6cf84862d1a8fbe25e295ff3a))

- Use collection id in download search_by_id
  ([#44](https://github.com/CS-SI/stac-fastapi-eodag/pull/44),
  [`479330c`](https://github.com/CS-SI/stac-fastapi-eodag/commit/479330c948174ebe2b50532c3710cb8d33daa85b))

- Use github repo for opentelemetry-instrumenation-eodag again
  ([`b608a7c`](https://github.com/CS-SI/stac-fastapi-eodag/commit/b608a7c8a8031830a83ec738c9bfc5d0cbe78923))

- Whoosh removed from eodag ([#47](https://github.com/CS-SI/stac-fastapi-eodag/pull/47),
  [`65d9e25`](https://github.com/CS-SI/stac-fastapi-eodag/commit/65d9e25c2c0bf5ab40597fea90e91a1699134ec6))

- **telemetry**: Simplify setup ([#51](https://github.com/CS-SI/stac-fastapi-eodag/pull/51),
  [`9aa7ea7`](https://github.com/CS-SI/stac-fastapi-eodag/commit/9aa7ea791a8ca463a2c45a5fadfa9eca998794c6))

### Testing

- Correct mock after upgrade to eodag 3.9
  ([#61](https://github.com/CS-SI/stac-fastapi-eodag/pull/61),
  [`3a2b677`](https://github.com/CS-SI/stac-fastapi-eodag/commit/3a2b677fa544f015e8f316c0700eb286f01c4238))


## v0.1.0 (2025-04-28)

- Initial Release
