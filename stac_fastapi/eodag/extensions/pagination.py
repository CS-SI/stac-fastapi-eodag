"""Pagination extension. Override to default page to 1."""

from dataclasses import dataclass
from typing import Annotated

import attr
from fastapi import Query
from pydantic import BaseModel
from stac_fastapi.extensions.core import PaginationExtension as BasePaginationExtension
from stac_fastapi.types.search import APIRequest


class POSTPagination(BaseModel):
    """Page based pagination for POST requests."""

    page: int = 1


@dataclass
class GETPagination(APIRequest):
    """Page based pagination for GET requests."""

    page: Annotated[int, Query()] = 1


@attr.s
class PaginationExtension(BasePaginationExtension):
    """
    Override pagination to define page attribute as an integer instead of a string
    """

    GET = GETPagination
    POST = POSTPagination
