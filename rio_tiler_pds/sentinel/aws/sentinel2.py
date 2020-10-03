"""AWS Sentinel 2 readers."""

import json
import re
from collections import OrderedDict
from typing import Dict, Tuple, Type

import attr
from rasterio.crs import CRS
from rasterio.features import bounds as featureBounds
from rasterio.warp import transform_geom

from rio_tiler import constants
from rio_tiler.errors import InvalidBandName
from rio_tiler.io import BaseReader, COGReader, MultiBandReader

from ... import get_object
from ..utils import s2_sceneid_parser

default_l1c_bands = (
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B09",
    "B11",
    "B12",
    "B8A",
)


@attr.s
class S2L1CReader(MultiBandReader):
    """AWS Public Dataset Sentinel 2 L1C reader.

    Args:
        sceneid (str): Sentinel-2 L1C sceneid.

    Attributes:
        minzoom (int): Dataset's Min Zoom level (default is 8).
        maxzoom (int): Dataset's Max Zoom level (default is 14).
        scene_params (dict): scene id parameters.
        bands (tuple): list of available bands (default is ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A')).
        tileInfo (dict): sentinel 2 tileInfo.json content.
        datageom (dict): sentinel 2 data geometry.

    Examples:
        >>> with S2L1CReader('S2A_L1C_20170729_19UDP_0') as scene:
                print(scene.bounds)

    """

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(default={"nodata": 0})
    minzoom: int = attr.ib(init=False, default=8)
    maxzoom: int = attr.ib(init=False, default=14)

    bands: Tuple = attr.ib(init=False, default=default_l1c_bands)
    tileInfo: Dict = attr.ib(init=False)
    datageom: Dict = attr.ib(init=False)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s2-l1c"
    _prefix: str = "tiles/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{_day}/{num}"

    def __attrs_post_init__(self):
        """Fetch productInfo and get bounds."""
        self.scene_params = s2_sceneid_parser(self.sceneid)

        prefix = self._prefix.format(**self.scene_params)
        self.tileInfo = json.loads(
            get_object(self._hostname, f"{prefix}/tileInfo.json", request_pays=True)
        )
        input_geom = self.tileInfo["tileDataGeometry"]
        input_crs = CRS.from_user_input(input_geom["crs"]["properties"]["name"])
        self.datageom = transform_geom(input_crs, constants.WGS84_CRS, input_geom)
        self.bounds = featureBounds(self.datageom)

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        band = band if len(band) == 3 else f"B0{band[-1]}"

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/{band}.jp2"


SENTINEL_L2_BANDS = OrderedDict(
    [
        ("10", ["B02", "B03", "B04", "B08"]),
        ("20", ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B11", "B12", "B8A"]),
        (
            "60",
            [
                "B01",
                "B02",
                "B03",
                "B04",
                "B05",
                "B06",
                "B07",
                "B08",
                "B09",
                "B11",
                "B12",
                "B8A",
            ],
        ),
    ]
)

SENTINEL_L2_PRODUCTS = OrderedDict(
    [
        ("10", ["AOT", "WVP"]),
        ("20", ["AOT", "SCL", "WVP"]),
        ("60", ["AOT", "SCL", "WVP"]),
    ]
)

default_l2a_bands = (
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B09",
    "B11",
    "B12",
    "B8A",
    # "AOT",
    # "SCL",
    # "WVP",
)


@attr.s
class S2L2AReader(S2L1CReader):
    """AWS Public Dataset Sentinel 2 L2A reader.

    Args:
        sceneid (str): Sentinel-2 L2A sceneid.

    Attributes:
        bands (tuple): list of available bands (default is ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A')).

    Examples:
        >>> with S2L1CReader('S2A_L1C_20170729_19UDP_0') as scene:
                print(scene.bounds)

    """

    bands: tuple = attr.ib(init=False, default=default_l2a_bands)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s2-l2a"
    _prefix: str = "tiles/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{_day}/{num}"

    def _get_resolution(self, band: str) -> str:
        """Return L2A resolution prefix"""
        if band.startswith("B"):
            for res, bands in SENTINEL_L2_BANDS.items():
                if band in bands:
                    break
        else:
            for res, bands in SENTINEL_L2_PRODUCTS.items():
                if band in bands:
                    break
        return res

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        band = band if len(band) == 3 else f"B0{band[-1]}"

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        res = self._get_resolution(band)
        return f"{self._scheme}://{self._hostname}/{prefix}/R{res}m/{band}.jp2"


@attr.s
class S2COGReader(MultiBandReader):
    """AWS Public Dataset Sentinel 2 COGS reader.

    Args:
        sceneid (str): Sentinel-2 sceneid.

    Attributes:
        minzoom (int): Dataset's Min Zoom level (default is 8).
        maxzoom (int): Dataset's Max Zoom level (default is 14).
        scene_params (dict): scene id parameters.
        bands (tuple): list of available bands (defined by the STAC item.json).
        stac_item (dict): sentinel 2 COG STAC item content.

    Examples:
        >>> with S2COGReader('S2A_29RKH_20200219_0_L2A') as scene:
                print(scene.bounds)

    """

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)
    minzoom: int = attr.ib(init=False, default=8)
    maxzoom: int = attr.ib(init=False, default=14)

    bands: tuple = attr.ib(init=False)
    stac_item: Dict = attr.ib(init=False)

    _scheme: str = "s3"
    _hostname: str = "sentinel-cogs"
    _prefix: str = "sentinel-s2-{_levelLow}-cogs/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{scene}"

    def __attrs_post_init__(self):
        """Fetch item.json and get bounds and bands."""
        self.scene_params = s2_sceneid_parser(self.sceneid)

        cog_sceneid = self.scene_params["scene"]
        prefix = self._prefix.format(**self.scene_params)
        self.stac_item = json.loads(
            get_object(
                self._hostname, f"{prefix}/{cog_sceneid}.json", request_pays=True
            )
        )
        self.bands = tuple(
            [band for band in self.stac_item["assets"] if re.match("B[0-9A]{2}", band)]
        )
        self.bounds = self.stac_item["bbox"]

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        band = band if len(band) == 3 else f"B0{band[-1]}"

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/{band}.tif"
