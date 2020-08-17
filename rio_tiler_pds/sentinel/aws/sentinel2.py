"""rio_tiler_pds.sentinel.awspds_sentinel2."""

import os
import json
import attr
from typing import Dict, Type
from collections import OrderedDict

from rasterio.crs import CRS
from rasterio.warp import transform_geom
from rasterio.features import bounds as featureBounds

from rio_tiler import constants
from rio_tiler.io import BaseReader, COGReader
from rio_tiler.errors import InvalidAssetName
from rio_tiler.utils import aws_get_object

from ...reader import MultiBandReader
from ..utils import s2_sceneid_parser


@attr.s
class S2L1CReader(MultiBandReader):
    """AWS Public Dataset Sentinel 2 L1C reader."""

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(default={"nodata": 0})
    minzoom: int = attr.ib(init=False, default=8)
    maxzoom: int = attr.ib(init=False, default=14)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s2-l1c"
    _prefix: str = "tiles/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{_day}/{num}"

    def __enter__(self):
        """Support using with Context Managers."""
        self.scene_params = s2_sceneid_parser(self.sceneid)

        tileinfo_key = os.path.join(
            self._prefix.format(**self.scene_params), "tileInfo.json"
        )

        # TODO: Should be cached
        self.tileInfo = json.loads(
            aws_get_object(self._hostname, tileinfo_key, request_pays=True)
        )
        input_geom = self.tileInfo["tileDataGeometry"]
        input_crs = CRS.from_user_input(input_geom["crs"]["properties"]["name"])
        self.datageom = transform_geom(
            input_crs, constants.WGS84_CRS, input_geom
        )
        self.bounds = featureBounds(self.datageom)

        self.assets = (
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
            ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B11", "B12", "B8A"],
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


@attr.s
class S2L2AReader(MultiBandReader):
    """AWS Public Dataset Sentinel 2 L2A reader."""

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(default={"nodata": 0})
    minzoom: int = attr.ib(init=False, default=8)
    maxzoom: int = attr.ib(init=False, default=14)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s2-l2a"
    _prefix: str = "tiles/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{_day}/{num}"

    def __enter__(self):
        """Support using with Context Managers."""
        self.scene_params = s2_sceneid_parser(self.sceneid)

        tileinfo_key = os.path.join(
            self._prefix.format(**self.scene_params), "tileInfo.json"
        )

        # TODO: Should be cached
        self.tileInfo = json.loads(
            aws_get_object(self._hostname, tileinfo_key, request_pays=True)
        )
        input_geom = self.tileInfo["tileDataGeometry"]
        input_crs = CRS.from_user_input(input_geom["crs"]["properties"]["name"])
        self.datageom = transform_geom(
            input_crs, constants.WGS84_CRS, input_geom
        )
        self.bounds = featureBounds(self.datageom)

        self.assets = (
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
            "AOT",
            "SCL",
            "WVP",
        )
        return self

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
class S2L2ACOGReader(MultiBandReader):
    """AWS Public Dataset Sentinel 2 L2A COGS reader."""

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)
    minzoom: int = attr.ib(init=False, default=8)
    maxzoom: int = attr.ib(init=False, default=14)

    _scheme: str = "s3"
    _hostname: str = "sentinel-cogs"
    _prefix: str = "sentinel-s2-l2a-cogs/{acquisitionYear}/{scene}"

    def __enter__(self):
        """Support using with Context Managers."""
        self.scene_params = s2_sceneid_parser(self.sceneid)

        tileinfo_key = os.path.join(
            self._prefix.format(**self.scene_params), f"{self.sceneid}.json"
        )

        # TODO: Should be cached
        self.tileInfo = json.loads(
            aws_get_object(self._hostname, tileinfo_key, request_pays=True)
        )
        self.bounds = self.tileInfo["bbox"]

        self.assets = (
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
            "AOT",
            "SCL",
            "WVP",
        )
        return self

    def _get_asset_url(self, asset: str) -> str:
        """Validate band name and return asset's url."""
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/{asset}.tif"
