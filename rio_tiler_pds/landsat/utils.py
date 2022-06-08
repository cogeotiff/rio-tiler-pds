"""Landsat utility functions."""

import re
from typing import Any, Dict, Tuple

import numpy

from rio_tiler_pds.errors import InvalidLandsatSceneId
from rio_toa import brightness_temp, reflectance

OLI_SR_BANDS: Tuple[str, ...] = (
    "QA_PIXEL",
    "QA_RADSAT",
    "SR_B1",
    "SR_B2",
    "SR_B3",
    "SR_B4",
    "SR_B5",
    "SR_B6",
    "SR_B7",
    "SR_QA_AEROSOL",
)

TIRS_ST_BANDS: Tuple[str, ...] = (
    "ST_ATRAN",
    "ST_B10",
    "ST_CDIST",
    "ST_DRAD",
    "ST_EMIS",
    "ST_EMSD",
    "ST_QA",
    "ST_TRAD",
    "ST_URAD",
)

TM_SR_BANDS: Tuple[str, ...] = (
    "QA_PIXEL",
    "QA_RADSAT",
    "SR_ATMOS_OPACITY",
    "SR_B1",
    "SR_B2",
    "SR_B3",
    "SR_B4",
    "SR_B5",
    "SR_B7",
    "SR_CLOUD_QA",
)

TM_ST_BANDS: Tuple[str, ...] = (
    "ST_ATRAN",
    "ST_B6",
    "ST_CDIST",
    "ST_DRAD",
    "ST_EMIS",
    "ST_EMSD",
    "ST_QA",
    "ST_TRAD",
    "ST_URAD",
)

OLI_L1_BANDS: Tuple[str, ...] = ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9")

TIRS_L1_BANDS: Tuple[str, ...] = ("B10", "B11")

OLI_L1_QA_BANDS: Tuple[str, ...] = (
    "QA_PIXEL",
    "QA_RADSAT",
    "SAA",
    "SZA",
    "VAA",
    "VZA",
)

TIRS_L1_QA_BANDS: Tuple[str, ...] = (
    "QA_PIXEL",
    "QA_RADSAT",
)

ETM_L1_BANDS: Tuple[str, ...] = (
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6_VCID_1",
    "B6_VCID_2",
    "B7",
    "B8",
    "QA_PIXEL",
    "QA_RADSAT",
    "SAA",
    "SZA",
    "VAA",
    "VZA",
)

TM_L1_BANDS: Tuple[str, ...] = (
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "QA_PIXEL",
    "QA_RADSAT",
    "SAA",
    "SZA",
    "VAA",
    "VZA",
)

MSS_L1_BANDS: Tuple[str, ...] = ("B4", "B5", "B6", "B7", "QA_PIXEL", "QA_RADSAT")


def sceneid_parser(sceneid: str) -> Dict:
    """Parse Landsat id.

    Author @perrygeo - http://www.perrygeo.com

    Args:
        sceneid (str): Landsat sceneid.

    Returns:
        dict: dictionary with metadata constructed from the sceneid.

    Raises:
        InvalidLandsatSceneId: If `sceneid` doesn't match the regex schema.

    Examples:
        >>> sceneid_parser('LC08_L1TP_016037_20170813_20170814_01_RT')

    """
    if not re.match(
        r"^L[COTEM]\d{2}_L\d{1}[A-Z]{2}_\d{6}_\d{8}_\d{8}_\d{2}_\w{2}$", sceneid
    ):
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

    meta: Dict[str, Any] = re.match(  # type: ignore
        collection_pattern, sceneid, re.IGNORECASE
    ).groupdict()

    meta["scene"] = sceneid
    meta["date"] = "{}-{}-{}".format(
        meta["acquisitionYear"], meta["acquisitionMonth"], meta["acquisitionDay"]
    )
    meta["_processingLevelNum"] = meta["processingCorrectionLevel"][1]

    if meta["sensor"] == "C":
        sensor_name = "oli-tirs"
    elif meta["sensor"] == "O":
        sensor_name = "oli"
    elif meta["sensor"] == "T" and int(meta["satellite"]) >= 8:
        sensor_name = "tirs"
    elif meta["sensor"] == "E":
        sensor_name = "etm"
    elif meta["sensor"] == "T" and int(meta["satellite"]) < 8:
        sensor_name = "tm"
    elif meta["sensor"] == "M":
        sensor_name = "mss"

    meta["category"] = (
        "albers" if meta["collectionCategory"] in ["A1", "A2"] else "standard"
    )

    # S3 paths always use oli-tirs
    _sensor_s3_prefix = sensor_name
    if _sensor_s3_prefix in ["oli", "tirs"]:
        _sensor_s3_prefix = "oli-tirs"

    meta["sensor_name"] = sensor_name
    meta["_sensor_s3_prefix"] = _sensor_s3_prefix
    meta["bands"] = get_bands_for_scene_meta(meta)

    return meta


def get_bands_for_scene_meta(meta: Dict) -> Tuple[str, ...]:  # noqa: C901
    """Get available Landsat bands given scene metadata"""
    sensor_name = meta["sensor_name"]

    if meta["processingCorrectionLevel"] == "L2SR":
        if sensor_name in ["oli-tirs", "oli"]:
            bands = OLI_SR_BANDS
        elif sensor_name in ["tm", "etm"]:
            bands = TM_SR_BANDS

    elif meta["processingCorrectionLevel"] == "L2SP":
        if sensor_name == "oli-tirs":
            bands = OLI_SR_BANDS + TIRS_ST_BANDS
        elif sensor_name in ["tm", "etm"]:
            bands = TM_SR_BANDS + TM_ST_BANDS

    # Level 1
    else:
        if sensor_name == "oli":
            bands = OLI_L1_BANDS + OLI_L1_QA_BANDS
        elif sensor_name == "tirs":
            bands = TIRS_L1_BANDS + TIRS_L1_QA_BANDS
        elif sensor_name == "oli-tirs":
            bands = OLI_L1_BANDS + TIRS_L1_BANDS + OLI_L1_QA_BANDS
        elif sensor_name == "etm":
            bands = ETM_L1_BANDS
        elif sensor_name == "tm":
            bands = TM_L1_BANDS
        elif sensor_name == "mss":
            bands = MSS_L1_BANDS

    return bands


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
