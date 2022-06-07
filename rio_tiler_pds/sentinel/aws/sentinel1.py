"""AWS Sentinel 1 reader."""

import json
from typing import Dict, Type

import attr
from morecantile import TileMatrixSet
from rasterio.features import bounds as featureBounds

from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import InvalidBandName
from rio_tiler.io import GCPCOGReader, MultiBandReader
from rio_tiler_pds.sentinel.utils import s1_sceneid_parser
from rio_tiler_pds.utils import get_object


@attr.s
class S1L1CReader(MultiBandReader):
    """AWS Public Dataset Sentinel 1 reader.

    Args:
        input (str): Sentinel-1 sceneid.

    Attributes:
        minzoom (int): Dataset's Min Zoom level (default is 8).
        maxzoom (int): Dataset's Max Zoom level (default is 14).
        bands (tuple): list of available bands (default is ('vv', 'vh')).
        productInfo (dict): sentinel 1 productInfo.json content.
        datageom (dict): sentinel 1 data geometry.

    Examples:
        >>> with S1L1CReader('S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B') as scene:
                print(scene.bounds)

    """

    input: str = attr.ib()
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    reader: Type[GCPCOGReader] = attr.ib(default=GCPCOGReader)
    reader_options: Dict = attr.ib(default={"nodata": 0})

    minzoom: int = attr.ib(default=8)
    maxzoom: int = attr.ib(default=14)

    productInfo: Dict = attr.ib(init=False)
    datageom: Dict = attr.ib(init=False)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="sentinel-s1-l1c")
    prefix_pattern: str = attr.ib(
        default="{product}/{acquisitionYear}/{_month}/{_day}/{beam}/{polarisation}/{scene}"
    )

    def __attrs_post_init__(self):
        """Fetch productInfo and get bounds."""
        self.scene_params = s1_sceneid_parser(self.input)
        if self.scene_params["polarisation"] == "DH":
            self.bands = ("hh", "hv")

        elif self.scene_params["polarisation"] == "DV":
            self.bands = ("vv", "vh")

        elif self.scene_params["polarisation"] == "SH":
            self.bands = ("hh",)

        elif self.scene_params["polarisation"] == "SV":
            self.bands = ("vv",)

        prefix = self.prefix_pattern.format(**self.scene_params)
        self.productInfo = json.loads(
            get_object(self.bucket, f"{prefix}/productInfo.json", request_pays=True)
        )

        self.datageom = self.productInfo["footprint"]
        self.bounds = featureBounds(self.datageom)
        self.crs = WGS84_CRS

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self.prefix_pattern.format(**self.scene_params)
        return f"{self._scheme}://{self.bucket}/{prefix}/measurement/{self.scene_params['beam'].lower()}-{band}.tiff"
