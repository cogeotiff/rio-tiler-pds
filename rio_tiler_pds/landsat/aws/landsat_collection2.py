"""AWS Landsat Collection 2 reader."""

import os
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Type, Union

import attr
import numpy
from morecantile import TileMatrixSet
from rasterio.enums import Resampling
from rasterio.io import DatasetReader

from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.errors import InvalidBandName, MissingBands, TileOutsideBounds
from rio_tiler.expression import apply_expression
from rio_tiler.io import COGReader, MultiBandReader
from rio_tiler.models import ImageData
from rio_tiler.tasks import multi_arrays
from rio_tiler.utils import pansharpening_brovey
from rio_toa import toa_utils

from ... import get_object
from ..utils import dn_to_toa, sceneid_parser

DEFAULT_L8SR_BANDS = (
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

DEFAULT_L8ST_BANDS = (
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

@attr.s
class L8L2SRReader(MultiBandReader):
    """AWS Public Dataset Landsat Collection 2 Level 2 Surface Reflectance COG Reader.

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

    """

    sceneid: str = attr.ib()
    reader: Type[COGReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(default={"nodata": 0})
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib(default=5)
    maxzoom: int = attr.ib(default=12)

    bands: Tuple = attr.ib(init=False)

    _scheme: str = "s3"
    _hostname: str = "usgs-landsat"
    _prefix: str = "tiles/level-{processingLevel}/standard/oli-tirs/{acquisitionYear}/{path}/{row}/{scene}/{scene}"

    def __attrs_post_init__(self):
        """Fetch productInfo and get bounds."""
        self.scene_params = sceneid_parser(self.sceneid)

        if not self.bands:
            if self.scene_params['processingCorrectionLevel'] == 'L2SR':
                self.bands = DEFAULT_L8SR_BANDS
            elif self.scene_params['processingCorrectionLevel'] == 'L2SP':
                self.bands = DEFAULT_L8SR_BANDS + DEFAULT_L8ST_BANDS

        # TODO: fetch STAC to get bounds (self.bounds must be set)
        # Allow custom function for users who want to use the WRS2 grid and
        # avoid this GET request.

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        # TODO: allow B1 instead of SR_B1

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid.\nValid bands: {self.bands}")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}_{band}.TIF"
