"""CBERS utility functions."""

import re
from typing import Any, Dict

from ..errors import InvalidCBERSSceneId


def sceneid_parser(sceneid: str) -> Dict:
    """Parse CBERS 4 scene id.

    Args:
        sceneid (str): CBERS 4 sceneid.

    Returns:
        dict: dictionary with metadata constructed from the sceneid.

    Raises:
        InvalidCBERSSceneId: If `sceneid` doesn't match the regex schema.

    Examples:
        >>> sceneid_parser('CBERS_4_MUX_20171121_057_094_L2')

    """
    if not re.match(r"^CBERS_4_\w+_[0-9]{8}_[0-9]{3}_[0-9]{3}_L[0-9]$", sceneid):
        raise InvalidCBERSSceneId("Could not match {}".format(sceneid))

    cbers_pattern = (
        r"(?P<satellite>\w+)_"
        r"(?P<mission>[0-9]{1})"
        r"_"
        r"(?P<instrument>\w+)"
        r"_"
        r"(?P<acquisitionYear>[0-9]{4})"
        r"(?P<acquisitionMonth>[0-9]{2})"
        r"(?P<acquisitionDay>[0-9]{2})"
        r"_"
        r"(?P<path>[0-9]{3})"
        r"_"
        r"(?P<row>[0-9]{3})"
        r"_"
        r"(?P<processingCorrectionLevel>L[0-9]{1})$"
    )

    meta: Dict[str, Any] = re.match(cbers_pattern, sceneid, re.IGNORECASE).groupdict()
    meta["scene"] = sceneid
    meta["date"] = "{}-{}-{}".format(
        meta["acquisitionYear"], meta["acquisitionMonth"], meta["acquisitionDay"]
    )

    instrument = meta["instrument"]
    instrument_params = {
        "MUX": {
            "reference_band": "B6",
            "bands": ("B5", "B6", "B7", "B8"),
            "rgb": ("B7", "B6", "B5"),
        },
        "AWFI": {
            "reference_band": "B14",
            "bands": ("B13", "B14", "B15", "B16"),
            "rgb": ("B15", "B14", "B13"),
        },
        "PAN10M": {
            "reference_band": "B4",
            "bands": ("B2", "B3", "B4"),
            "rgb": ("B3", "B4", "B2"),
        },
        "PAN5M": {"reference_band": "B1", "bands": ("B1",), "rgb": ("B1", "B1", "B1")},
    }
    meta["reference_band"] = instrument_params[instrument]["reference_band"]
    meta["bands"] = instrument_params[instrument]["bands"]
    meta["rgb"] = instrument_params[instrument]["rgb"]

    return meta
