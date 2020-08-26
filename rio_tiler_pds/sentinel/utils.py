"""Sentinel 1 & 2 utility functions."""

import re
from typing import Any, Dict

from ..errors import InvalidSentinelSceneId


def s2_sceneid_parser(sceneid: str) -> Dict:
    """Parse Sentinel 2 scene id.

    Args:
        sceneid (str): Sentinel-2 sceneid.

    Returns:
        dict: dictionary with metadata constructed from the sceneid.

    Raises:
        InvalidSentinelSceneId: If `sceneid` doesn't match the regex schema.

    Examples:
        >>> s2_sceneid_parser('S2A_L1C_20170729_19UDP_0')

        >>> s2_sceneid_parser('S2A_L2A_20170729_19UDP_0')

        >>> s2_sceneid_parser('S2A_29RKH_20200219_0_L2A')

    """
    if re.match(
        "^S2[AB]_L[0-2][A-C]_[0-9]{8}_[0-9]{2}[A-Z]{3}_[0-9]$", sceneid
    ):  # Legacy sceneid format
        pattern = (
            r"^S"
            r"(?P<sensor>\w{1})"
            r"(?P<satellite>[AB]{1})"
            r"_"
            r"(?P<processingLevel>L[0-2][ABC])"
            r"_"
            r"(?P<acquisitionYear>[0-9]{4})"
            r"(?P<acquisitionMonth>[0-9]{2})"
            r"(?P<acquisitionDay>[0-9]{2})"
            r"_"
            r"(?P<utm>[0-9]{2})"
            r"(?P<lat>\w{1})"
            r"(?P<sq>\w{2})"
            r"_"
            r"(?P<num>[0-9]{1})$"
        )

    elif re.match(
        "^S2[AB]_[0-9]{2}[A-Z]{3}_[0-9]{8}_[0-9]_L[0-2][A-C]$", sceneid
    ):  # New sceneid format
        pattern = (
            r"^S"
            r"(?P<sensor>\w{1})"
            r"(?P<satellite>[AB]{1})"
            r"_"
            r"(?P<utm>[0-9]{2})"
            r"(?P<lat>\w{1})"
            r"(?P<sq>\w{2})"
            r"_"
            r"(?P<acquisitionYear>[0-9]{4})"
            r"(?P<acquisitionMonth>[0-9]{2})"
            r"(?P<acquisitionDay>[0-9]{2})"
            r"_"
            r"(?P<num>[0-9]{1})"
            r"_"
            r"(?P<processingLevel>L[0-2][ABC])$"
        )
    else:
        raise InvalidSentinelSceneId("Could not match {}".format(sceneid))

    meta: Dict[str, Any] = re.match(pattern, sceneid, re.IGNORECASE).groupdict()
    meta[
        "scene"
    ] = "S{sensor}{satellite}_{utm}{lat}{sq}_{acquisitionYear}{acquisitionMonth}{acquisitionDay}_{num}_{processingLevel}".format(
        **meta
    )
    meta["date"] = "{}-{}-{}".format(
        meta["acquisitionYear"], meta["acquisitionMonth"], meta["acquisitionDay"]
    )

    meta["_utm"] = meta["utm"].lstrip("0")
    meta["_month"] = meta["acquisitionMonth"].lstrip("0")
    meta["_day"] = meta["acquisitionDay"].lstrip("0")
    meta["_levelLow"] = meta["processingLevel"].lower()

    return meta


def s1_sceneid_parser(sceneid: str) -> Dict:
    """Parse Sentinel 1 scene id.

    Args:
        sceneid (str): Sentinel-1 sceneid.

    Returns:
        dict: dictionary with metadata constructed from the sceneid.

    Raises:
        InvalidSentinelSceneId: If `sceneid` doesn't match the regex schema.

    Examples:
        >>> s1_sceneid_parser('S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B')

    """
    if not re.match(
        "^S1[AB]_(IW)|(EW)_[A-Z]{3}[FHM]_[0-9][SA][A-Z]{2}_[0-9]{8}T[0-9]{6}_[0-9]{8}T[0-9]{6}_[0-9A-Z]{6}_[0-9A-Z]{6}_[0-9A-Z]{4}$",
        sceneid,
    ):
        raise InvalidSentinelSceneId("Could not match {}".format(sceneid))

    sentinel_pattern = (
        r"^S"
        r"(?P<sensor>\w{1})"
        r"(?P<satellite>[AB]{1})"
        r"_"
        r"(?P<beam>[A-Z]{2})"
        r"_"
        r"(?P<product>[A-Z]{3})"
        r"(?P<resolution>[FHM])"
        r"_"
        r"(?P<processing_level>[0-9])"
        r"(?P<product_class>[SA])"
        r"(?P<polarisation>(SH)|(SV)|(DH)|(DV)|(HH)|(HV)|(VV)|(VH))"
        r"_"
        r"(?P<startDateTime>[0-9]{8}T[0-9]{6})"
        r"_"
        r"(?P<stopDateTime>[0-9]{8}T[0-9]{6})"
        r"_"
        r"(?P<absolute_orbit>[0-9]{6})"
        r"_"
        r"(?P<mission_task>[0-9A-Z]{6})"
        r"_"
        r"(?P<product_id>[0-9A-Z]{4})$"
    )

    meta: Dict[str, Any] = re.match(
        sentinel_pattern, sceneid, re.IGNORECASE
    ).groupdict()

    meta["acquisitionYear"] = meta["startDateTime"][0:4]
    meta["acquisitionMonth"] = meta["startDateTime"][4:6]
    meta["acquisitionDay"] = meta["startDateTime"][6:8]

    meta["scene"] = sceneid
    meta["date"] = "{}-{}-{}".format(
        meta["acquisitionYear"], meta["acquisitionMonth"], meta["acquisitionDay"]
    )
    meta["_month"] = meta["acquisitionMonth"].lstrip("0")
    meta["_day"] = meta["acquisitionDay"].lstrip("0")
    return meta
