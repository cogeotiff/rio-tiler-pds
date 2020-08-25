"""Landsat utility functions."""

import re
from typing import Any, Dict

import numpy
from rio_toa import brightness_temp, reflectance

from ..errors import InvalidLandsatSceneId


def sceneid_parser(sceneid: str) -> Dict:
    """Parse Landsat 8 scene id.

    Author @perrygeo - http://www.perrygeo.com

    Args:
        sceneid (str): Landsat 8 sceneid.

    Returns:
        dict: dictionary with metadata constructed from the sceneid.

    Raises:
        InvalidLandsatSceneId: If `sceneid` doesn't match the regex schema.

    Examples:
        >>> sceneid_parser('LC08_L1TP_016037_20170813_20170814_01_RT')

    """
    collection_1 = r"^L[COTEM]0[0-9]_L\d{1}[A-Z]{2}_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2|RT)$"
    if not re.match(collection_1, sceneid):
        raise InvalidLandsatSceneId("Could not match {}".format(sceneid))

    collection_pattern = (
        r"^L"
        r"(?P<sensor>\w{1})"
        r"(?P<satellite>\w{2})"
        r"_"
        r"(?P<processingCorrectionLevel>\w{4})"
        r"_"
        r"(?P<path>[0-9]{3})"
        r"(?P<row>[0-9]{3})"
        r"_"
        r"(?P<acquisitionYear>[0-9]{4})"
        r"(?P<acquisitionMonth>[0-9]{2})"
        r"(?P<acquisitionDay>[0-9]{2})"
        r"_"
        r"(?P<processingYear>[0-9]{4})"
        r"(?P<processingMonth>[0-9]{2})"
        r"(?P<processingDay>[0-9]{2})"
        r"_"
        r"(?P<collectionNumber>\w{2})"
        r"_"
        r"(?P<collectionCategory>\w{2})$"
    )

    meta: Dict[str, Any] = re.match(
        collection_pattern, sceneid, re.IGNORECASE
    ).groupdict()

    meta["scene"] = sceneid
    meta["date"] = "{}-{}-{}".format(
        meta["acquisitionYear"], meta["acquisitionMonth"], meta["acquisitionDay"]
    )

    return meta


def dn_to_toa(arr: numpy.ndarray, band: str, metadata: Dict) -> numpy.ndarray:
    """Convert DN to TOA or Temp.

    Args:
        arr (numpy.ndarray): Digital Number array values.
        band (str): Landsat 8 band's name.
        metadata (str): Landsat MTL metadata.

    Returns:
        numpy.ndarray: DN coverted to TOA or Temperature.

    """
    if band in ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]:  # OLI
        multi_reflect = metadata["RADIOMETRIC_RESCALING"].get(
            f"REFLECTANCE_MULT_BAND_{band[1:]}"
        )
        add_reflect = metadata["RADIOMETRIC_RESCALING"].get(
            f"REFLECTANCE_ADD_BAND_{band[1:]}"
        )
        sun_elev = metadata["IMAGE_ATTRIBUTES"]["SUN_ELEVATION"]

        arr = 10000 * reflectance.reflectance(
            arr, multi_reflect, add_reflect, sun_elev, src_nodata=0
        )
        arr = arr.astype("uint16")

    elif band in ["B10", "B11"]:  # TIRS
        multi_rad = metadata["RADIOMETRIC_RESCALING"].get(
            f"RADIANCE_MULT_BAND_{band[1:]}"
        )
        add_rad = metadata["RADIOMETRIC_RESCALING"].get(f"RADIANCE_ADD_BAND_{band[1:]}")
        k1 = metadata["TIRS_THERMAL_CONSTANTS"].get(f"K1_CONSTANT_BAND_{band[1:]}")
        k2 = metadata["TIRS_THERMAL_CONSTANTS"].get(f"K2_CONSTANT_BAND_{band[1:]}")

        arr = brightness_temp.brightness_temp(arr, multi_rad, add_rad, k1, k2)

    return arr
