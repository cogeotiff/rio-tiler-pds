"""rio_tiler_pds.sentinel.utils."""

import re
from ..errors import InvalidSentinelSceneId
from typing import Dict, Any


def s2_sceneid_parser(sceneid: str) -> Dict:
    """
    Parse Sentinel-2 scene id.

    Attributes
    ----------
    sceneid: str
        Sentinel-2 sceneid.

    Returns
    -------
    out: dict
        dictionary with metadata constructed from the sceneid.

    """    
    if re.match("^S2[AB]_L[0-2][A-C]_[0-9]{8}_[0-9]{2}[A-Z]{3}_[0-9]$", sceneid):
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

    elif re.match("^S2[AB]_[0-9]{2}[A-Z]{3}_[0-9]{8}_[0-9]_L[0-2][A-C]$", sceneid):
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
    meta["scene"] = sceneid
    meta["date"] = "{}-{}-{}".format(
        meta["acquisitionYear"], meta["acquisitionMonth"], meta["acquisitionDay"]
    )

    meta["_utm"] = meta["utm"].lstrip("0")
    meta["_month"] = meta["acquisitionMonth"].lstrip("0")
    meta["_day"] = meta["acquisitionDay"].lstrip("0")

    return meta


def s1_sceneid_parser(sceneid: str) -> Dict:
    """
    Parse Sentinel-1 scene id.

    Attributes
    ----------
    sceneid: str
        Sentinel-1 sceneid.

    Returns
    -------
    out: dict
        dictionary with metadata constructed from the sceneid.

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
