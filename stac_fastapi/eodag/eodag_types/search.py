"""stac_fastapi.types.search module."""

from typing import Optional

from geojson_pydantic.geometries import Polygon
from stac_fastapi.types.rfc3339 import str_to_interval
from stac_fastapi.types.search import BaseSearchPostRequest


class EodagSearch(BaseSearchPostRequest):
    """Search model.

    Overrides the validation for datetime and spatial filter from the base request model.
    """

    @property
    def start_date(self) -> Optional[str]:
        """Extract the start date from the datetime string."""
        if self.datetime and "/" in self.datetime:
            interval = str_to_interval(self.datetime)
        else:
            return self.datetime

        return interval[0].isoformat() if interval[0] else None

    @property
    def end_date(self) -> Optional[str]:
        """Extract the end date from the datetime string."""
        if self.datetime and "/" in self.datetime:
            interval = str_to_interval(self.datetime)
        else:
            return self.datetime

        return interval[1].isoformat() if interval[1] else None

    @property
    def spatial_filter(self) -> Optional[str]:
        """Return a geojson-pydantic object representing the spatial filter for the search
        request.

        Check for both because the ``bbox`` and ``intersects`` parameters are
        mutually exclusive.
        """
        if self.bbox:
            return Polygon.from_bounds(self.bbox[0], self.bbox[3], self.bbox[2], self.bbox[1]).wkt
        if self.intersects:
            return self.intersects.wkt
        return None
