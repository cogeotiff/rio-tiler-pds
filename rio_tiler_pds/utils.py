"""rio_tiler_pds.utils."""

import json
import os
import warnings
from functools import lru_cache
from typing import Any, Dict
from urllib.parse import urlparse

import httpx
from boto3.session import Session as boto3_session


def aws_get_object(
    bucket: str,
    key: str,
    request_pays: bool = False,
    client: "boto3_session.client" = None,
) -> bytes:
    """AWS s3 get object content."""
    if not client:
        if profile_name := os.environ.get("AWS_PROFILE", None):
            session = boto3_session(profile_name=profile_name)

        else:
            access_key = os.environ.get("AWS_ACCESS_KEY_ID", None)
            secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
            access_token = os.environ.get("AWS_SESSION_TOKEN", None)

            # AWS_REGION is GDAL specific. Later overloaded by standard AWS_DEFAULT_REGION
            region_name = os.environ.get(
                "AWS_DEFAULT_REGION", os.environ.get("AWS_REGION", None)
            )

            session = boto3_session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_access_key,
                aws_session_token=access_token,
                region_name=region_name or None,
            )

        # AWS_S3_ENDPOINT and AWS_HTTPS are GDAL config options of vsis3 driver
        # https://gdal.org/user/virtual_file_systems.html#vsis3-aws-s3-files
        endpoint_url = os.environ.get("AWS_S3_ENDPOINT", None)
        if endpoint_url:
            use_https = os.environ.get("AWS_HTTPS", "YES")
            if use_https.upper() in ["YES", "TRUE", "ON"]:
                endpoint_url = "https://" + endpoint_url

            else:
                endpoint_url = "http://" + endpoint_url

        client = session.client("s3", endpoint_url=endpoint_url)

    params = {"Bucket": bucket, "Key": key}
    if request_pays or os.environ.get("AWS_REQUEST_PAYER", "").lower() == "requester":
        params["RequestPayer"] = "requester"

    response = client.get_object(**params)
    return response["Body"].read()


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
