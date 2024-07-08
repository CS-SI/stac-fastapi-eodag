"""Collection Search extension."""

from enum import Enum
from typing import Annotated, List, Optional

import attr
from fastapi import FastAPI, Query
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.rfc3339 import DateTimeType, str_to_interval
from stac_fastapi.types.search import APIRequest, str2bbox
from stac_pydantic.shared import BBox


class CollectionSearchConformanceClasses(str, Enum):
    """Conformance classes for the Collection Search extension.

    See
    https://github.com/stac-api-extensions/collection-search
    """

    BASICS = "http://www.opengis.net/spec/ogcapi-common-2/1.0/conf/simple-query"
    FREETEXT_SEARCH = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#free-text"
    FILTER = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#filter"
    QUERY = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#query"
    SORT = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#sort"
    FIELDS = "https://api.stacspec.org/v1.0.0-rc.1/collection-search#fields"


@attr.s
class CollectionSearchExtensionGetRequest(APIRequest):
    """Collection Search extension GET request model."""

    limit: Annotated[Optional[int], Query()] = attr.ib(default=None)
    bbox: Annotated[Optional[BBox], Query()] = attr.ib(default=None, converter=str2bbox)
    datetime: Annotated[Optional[DateTimeType], Query()] = attr.ib(default=None, converter=str_to_interval)
    q: Annotated[Optional[str], Query()] = attr.ib(default=None)

# TODO: make q and datetime work

@attr.s
class CollectionSearchExtension(ApiExtension):
    """Collection Search extension.

    The Collection Search endpoint by default doesn't provide any query parameters
    to filter and all additional behavior will be defined in extensions.

    https://github.com/stac-api-extensions/collection-search/blob/main/README.md

    Attributes:
        conformance_classes: Conformance classes provided by the extension
    """

    GET = CollectionSearchExtensionGetRequest

    conformance_classes: List[str] = attr.ib(
        default=[
            CollectionSearchConformanceClasses.BASICS,
            CollectionSearchConformanceClasses.FREETEXT_SEARCH,
        ]
    )

    def register(self, app: FastAPI) -> None:
        """Register the extension with a FastAPI application.

        Args:
            app (fastapi.FastAPI): target FastAPI application.

        Returns:
            None
        """
        pass
