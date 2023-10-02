import attr
from typing import Optional
from pydantic import BaseModel
from stac_fastapi.types.search import APIRequest


class POSTPagination(BaseModel):
    """Page based pagination for POST requests."""

    page: Optional[int] = None


@attr.s
class GETPagination(APIRequest):
    """Page based pagination for GET requests."""

    page: Optional[int] = attr.ib(default=None)
