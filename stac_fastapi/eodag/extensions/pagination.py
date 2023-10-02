import attr
from stac_fastapi.extensions.core import PaginationExtension as BasePaginationExtension

from stac_fastapi.eodag.models.pagination import GETPagination, POSTPagination


@attr.s
class PaginationExtension(BasePaginationExtension):
    """
    Override pagination to define page attribute as an integer instead of a string
    """

    GET = GETPagination
    POST = POSTPagination
