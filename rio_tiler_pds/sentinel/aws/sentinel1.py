"""rio_tiler.io.sentinel1: Sentinel-1 processing."""

import os
import json
import attr
from typing import Any, Dict, Sequence, Union, Optional, Type

import rasterio
from rasterio import transform
from rasterio.features import bounds as featureBounds
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

from rio_tiler import constants
from rio_tiler.io import BaseReader, COGReader
from rio_tiler.errors import InvalidAssetName
from rio_tiler.utils import aws_get_object

from ...reader import MultiBandReader
from ..utils import s1_sceneid_parser


@attr.s
class GCPCOGReader(COGReader):
    """Custom COG Reader with GCPS support."""

    def __enter__(self):
        """Support using with Context Managers."""
        self.src_dataset = rasterio.open(self.filepath)
        self.dataset = WarpedVRT(
            self.src_dataset,
            src_crs=self.src_dataset.gcps[1],
            src_transform=transform.from_gcps(self.src_dataset.gcps[0]),
            src_nodata=0,
        )

        self.bounds = transform_bounds(
            self.dataset.crs, constants.WGS84_CRS, *self.dataset.bounds, densify_pts=21
        )

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers."""
        self.dataset.close()
        self.src_dataset.close()


@attr.s
class S1CReader(MultiBandReader):
    """AWS Public Dataset Sentinel 1 reader."""

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=GCPCOGReader)
    reader_options: Dict = attr.ib(factory=dict)
    minzoom: int = attr.ib(init=False, default=8)
    maxzoom: int = attr.ib(init=False, default=14)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s1-l1c"
    _prefix: str = "{product}/{acquisitionYear}/{_month}/{_day}/{beam}/{polarisation}/{scene}"

    def __enter__(self):
        """Support using with Context Managers."""
        self.scene_params = s1_sceneid_parser(self.sceneid)

        productinfo_key = os.path.join(
            self._prefix.format(**self.scene_params), "productInfo.json"
        )

        # TODO: Should be cached
        self.productInfo = json.loads(
            aws_get_object(self._hostname, productinfo_key, request_pays=True)
        )
        self.datageom = self.productInfo["footprint"]
        self.bounds = featureBounds(self.datageom)
        self.assets = ("vv", "vh")
        return self

    def _get_asset_url(self, asset: str) -> str:
        """Validate band name and return asset's url."""
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/measurement/{self.scene_params['beam'].lower()}-{asset}.tiff"
