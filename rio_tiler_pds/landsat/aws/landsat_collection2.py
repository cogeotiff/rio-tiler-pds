"""AWS Landsat Collection 2 reader."""

import json
from typing import Any, Dict, Tuple, Type

import attr
from morecantile import TileMatrixSet

from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.errors import InvalidBandName
from rio_tiler.io import COGReader, MultiBandReader

from ... import get_object
from ..utils import sceneid_parser

OLI_TIRS_SR_BANDS = (
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

OLI_TIRS_ST_BANDS = (
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

# For collection 2, level 2, ETM and TM have the same bands
TM_SR_BANDS = (
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

TM_ST_BANDS = (
    "QA_PIXEL",
    "QA_RADSAT",
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


@attr.s
class LandsatC2L2Reader(MultiBandReader):
    """AWS Public Dataset Landsat Collection 2 Level 2 COG Reader.

    Args:
        sceneid (str): Landsat 8 sceneid.

    Attributes:
        minzoom (int): Dataset's Min Zoom level (default is 5).
        maxzoom (int): Dataset's Max Zoom level (default is 12).
        scene_params (dict): scene id parameters.
        bands (tuple): list of available bands.

    Examples:
        >>> with L8C2COGReader('LC08_L2SR_093106_20200207_20201016_02_T2') as scene:
                print(scene.bounds)

        >>> with L8C2COGReader('LC08_L1TP_116043_20201122_20201122_02_RT') as scene:
                print(scene.bounds)

    """

    sceneid: str = attr.ib()
    reader: Type[COGReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(default={})
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib(default=5)
    maxzoom: int = attr.ib(default=12)

    bands: Tuple = attr.ib(init=False)

    _scheme: str = "s3"
    _hostname: str = "usgs-landsat"
    _prefix: str = "collection02/level-{_processingLevelNum}/standard/{_sensor}/{acquisitionYear}/{path}/{row}/{scene}/{scene}"

    def __attrs_post_init__(self):
        """Fetch productInfo and get bounds."""
        self.scene_params = sceneid_parser(self.sceneid)

        processing_level = self.scene_params["processingCorrectionLevel"]
        sensor = self.scene_params["_sensor"]

        # For collection 2, level 2, ETM and TM have the same bands
        if processing_level == "L2SR":
            if sensor == "oli-tirs":
                self.bands = OLI_TIRS_SR_BANDS
            elif sensor == "tm":
                self.bands = TM_SR_BANDS
            elif sensor == "etm":
                self.bands = TM_SR_BANDS
        else:
            if sensor == "oli-tirs":
                self.bands = OLI_TIRS_SR_BANDS + OLI_TIRS_ST_BANDS
            elif sensor == "tm":
                self.bands = TM_SR_BANDS + TM_ST_BANDS
            elif sensor == "etm":
                self.bands = TM_SR_BANDS + TM_ST_BANDS
        # TODO: add separate level 1 reader with TOA reflectances
        # elif self.scene_params['processingCorrectionLevel'] in ['L1TP', 'L1GT', 'L1GS']:
        #     self.bands = DEFAULT_L8L1_BANDS

        self._get_geometry()

    def _get_geometry(self):
        # TODO: fetch STAC to get bounds (self.bounds must be set)
        # Allow custom function for users who want to use the WRS2 grid and
        # avoid this GET request.
        prefix = self._prefix.format(**self.scene_params)

        # This fetches the Surface Reflectance (SR) STAC item.
        # There are separate STAC items for Surface Reflectance and Surface
        # Temperature (ST), but they have the same geometry. The SR should
        # always exist, the ST might not exist based on the scene.
        self.stac_item = json.loads(
            get_object(self._hostname, f"{prefix}_SR_stac.json", request_pays=True)
        )
        self.bounds = self.stac_item["bbox"]

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        # TODO: allow B1 instead of SR_B1

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid.\nValid bands: {self.bands}")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}_{band}.TIF"


def LandsatC2Reader(sceneid: str, **kwargs: Any) -> LandsatC2L2Reader:
    """Landsat Collection 2 COG readers."""
    scene_params = sceneid_parser(sceneid)
    level = scene_params["_processingLevelNum"]
    if level == "2":
        return LandsatC2L2Reader(sceneid, **kwargs)
    else:
        raise NotImplementedError(f"Level-{level} is not yet implemented")
