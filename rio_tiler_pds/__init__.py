"""rio-tiler-pds."""

from functools import lru_cache

from rio_tiler.utils import aws_get_object

__version__ = "0.3.2"


@lru_cache(maxsize=512)
def get_object(bucket: str, key: str, request_pays: bool = False) -> bytes:
    """Add LRU cache on top of AWS Get Object."""
    return aws_get_object(bucket, key, request_pays=request_pays)
