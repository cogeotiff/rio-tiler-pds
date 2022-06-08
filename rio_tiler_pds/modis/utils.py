"""MODIS utility functions."""

import re
from typing import Any, Dict

from rio_tiler_pds.errors import InvalidMODISSceneId


def sceneid_parser(sceneid: str) -> Dict:
    """Parse MODIS scene id.

    Args:
        sceneid (str): Sentinel-2 sceneid.

    Returns:
        dict: dictionary with metadata constructed from the sceneid.

    Raises:
        InvalidMODISSceneId: If `sceneid` doesn't match the regex schema.

    Examples:
        >>> sceneid_parser('MCD43A4.A2017006.h21v11.006.2017018074804')

    """
    if re.match(
        r"^M[COY]D[0-9]{2}[A-Z0-9]{2}\.A[0-9]{4}[0-9]{3}\.h[0-9]{2}v[0-9]{2}\.[0-9]{3}\.[0-9]{13}$",
        sceneid,
    ):
        pattern = (
            r"^(?P<product>M[COY]D[0-9]{2}[A-Z0-9]{2})"
            r"\."
            r"A(?P<date>[0-9]{4}[0-9]{3})"
            r"\."
            r"h(?P<horizontal_grid>[0-9]{2})"
            r"v(?P<vertical_grid>[0-9]{2})"
            r"\."
            r"(?P<version>[0-9]{3})"
            r"\."
            r"(?P<acquisitionYear>[0-9]{4})"
            r"(?P<acquisitionDOY>[0-9]{3})"
            r"[0-9]{6}$"
        )
    else:
        raise InvalidMODISSceneId("Could not match {}".format(sceneid))

    meta: Dict[str, Any] = re.match(pattern, sceneid, re.IGNORECASE).groupdict()  # type: ignore
    meta["scene"] = sceneid
    return meta
