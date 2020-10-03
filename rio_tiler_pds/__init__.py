"""rio-tiler-pds."""

from functools import lru_cache

import pkg_resources

from rio_tiler.utils import aws_get_object

version = pkg_resources.get_distribution(__package__).version


@lru_cache(maxsize=512)
def get_object(bucket: str, key: str, request_pays: bool = False) -> bytes:
    """Add LRU cache on top of AWS Get Object."""
    return aws_get_object(bucket, key, request_pays=request_pays)
