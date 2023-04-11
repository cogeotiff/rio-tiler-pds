"""rio_tiler_pds.utils."""

import json
import warnings
from functools import lru_cache
from typing import Any, Dict
from urllib.parse import urlparse

import httpx

from rio_tiler.utils import aws_get_object


@lru_cache(maxsize=512)
def get_object(bucket: str, key: str, request_pays: bool = False) -> bytes:
    """Add LRU cache on top of AWS Get Object."""
    warnings.warn(
        "`rio_tiler_pds.utils.get_object` will be removed in version 1.0, Please use `rio_tiler_pds.utils.fetch`",
        DeprecationWarning,
    )
    return aws_get_object(bucket, key, request_pays=request_pays)


@lru_cache(maxsize=512)
def fetch(filepath: str, **kwargs: Any) -> Dict:
    """Fetch URL.

    A LRU cache is set on top of this function.

    Args:
        filepath (str): URL.
        kwargs (any): additional options to pass to client.

    Returns:
        dict: URL JSON content.

    """
    parsed = urlparse(filepath)
    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path.strip("/")
        return json.loads(aws_get_object(bucket, key, **kwargs))

    elif parsed.scheme in ["https", "http", "ftp"]:
        resp = httpx.get(filepath, **kwargs)
        resp.raise_for_status()
        return resp.json()

    else:
        with open(filepath, "r") as f:
            return json.load(f)
