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
from rio_tiler.errors import InvalidAssetName
from rio_tiler.io import BaseReader, COGReader

from ...reader import MultiBandReader, get_object
from ..utils import s2_sceneid_parser

default_l1c_assets = (
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
        assets (tuple): list of available assets (default is ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A')).
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

    assets: Tuple = attr.ib(init=False, default=default_l1c_assets)
    tileInfo: Dict = attr.ib(init=False)
    datageom: Dict = attr.ib(init=False)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s2-l1c"
    _prefix: str = "tiles/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{_day}/{num}"

    def __enter__(self):
        """Support using with Context Managers."""
        self.scene_params = s2_sceneid_parser(self.sceneid)

        prefix = self._prefix.format(**self.scene_params)
        self.tileInfo = json.loads(
            get_object(self._hostname, f"{prefix}/tileInfo.json", request_pays=True)
        )
        input_geom = self.tileInfo["tileDataGeometry"]
        input_crs = CRS.from_user_input(input_geom["crs"]["properties"]["name"])
        self.datageom = transform_geom(input_crs, constants.WGS84_CRS, input_geom)
        self.bounds = featureBounds(self.datageom)
        return self

    def _get_asset_url(self, asset: str) -> str:
        """Validate band name and return asset's url."""
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/{asset}.jp2"


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

default_l2a_assets = (
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
        assets (tuple): list of available assets (default is ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A')).

    Examples:
        >>> with S2L1CReader('S2A_L1C_20170729_19UDP_0') as scene:
                print(scene.bounds)

    """

    assets: tuple = attr.ib(init=False, default=default_l2a_assets)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s2-l2a"
    _prefix: str = "tiles/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{_day}/{num}"

    def _get_resolution(self, asset: str) -> str:
        """Return L2A resolution prefix"""
        if asset.startswith("B"):
            for res, bands in SENTINEL_L2_BANDS.items():
                if asset in bands:
                    break
        else:
            for res, bands in SENTINEL_L2_PRODUCTS.items():
                if asset in bands:
                    break
        return res

    def _get_asset_url(self, asset: str) -> str:
        """Validate band name and return asset's url."""
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")
        prefix = self._prefix.format(**self.scene_params)
        res = self._get_resolution(asset)
        return f"{self._scheme}://{self._hostname}/{prefix}/R{res}m/{asset}.jp2"


@attr.s
class S2COGReader(MultiBandReader):
    """AWS Public Dataset Sentinel 2 COGS reader.

    Args:
        sceneid (str): Sentinel-2 sceneid.

    Attributes:
        minzoom (int): Dataset's Min Zoom level (default is 8).
        maxzoom (int): Dataset's Max Zoom level (default is 14).
        scene_params (dict): scene id parameters.
        assets (tuple): list of available assets (defined by the STAC item.json).
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

    assets: tuple = attr.ib(init=False)
    stac_item: Dict = attr.ib(init=False)

    _scheme: str = "s3"
    _hostname: str = "sentinel-cogs"
    _prefix: str = "sentinel-s2-{_levelLow}-cogs/{acquisitionYear}/{scene}"

    def __enter__(self):
        """Support using with Context Managers."""
        self.scene_params = s2_sceneid_parser(self.sceneid)

        cog_sceneid = self.scene_params["scene"]
        prefix = self._prefix.format(**self.scene_params)
        self.stac_item = json.loads(
            get_object(
                self._hostname, f"{prefix}/{cog_sceneid}.json", request_pays=True
            )
        )
        self.assets = tuple(
            [
                asset
                for asset in self.stac_item["assets"]
                if re.match("B[0-9A]{2}", asset)
            ]
        )
        self.bounds = self.stac_item["bbox"]

        return self

    def _get_asset_url(self, asset: str) -> str:
        """Validate band name and return asset's url."""
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/{asset}.tif"
