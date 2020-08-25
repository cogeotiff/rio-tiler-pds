"""rio_tiler.io.sentinel1: Sentinel-1 processing."""

import json
import os
from typing import Dict, Tuple, Type

import attr
from rasterio.features import bounds as featureBounds

from rio_tiler.errors import InvalidAssetName
from rio_tiler.io import BaseReader

from ...reader import GCPCOGReader, MultiBandReader, get_object
from ..utils import s1_sceneid_parser


@attr.s
class S1L1CReader(MultiBandReader):
    """AWS Public Dataset Sentinel 1 reader."""

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=GCPCOGReader)
    reader_options: Dict = attr.ib(factory=dict)
    minzoom: int = attr.ib(init=False, default=8)
    maxzoom: int = attr.ib(init=False, default=14)

    assets: Tuple = attr.ib(init=False, default=("vv", "vh"))
    productInfo: Dict = attr.ib(init=False)
    datageom: Dict = attr.ib(init=False)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s1-l1c"
    _prefix: str = "{product}/{acquisitionYear}/{_month}/{_day}/{beam}/{polarisation}/{scene}"

    def __enter__(self):
        """Support using with Context Managers."""
        self.scene_params = s1_sceneid_parser(self.sceneid)

        productinfo_key = os.path.join(
            self._prefix.format(**self.scene_params), "productInfo.json"
        )

        self.productInfo = json.loads(
            get_object(self._hostname, productinfo_key, request_pays=True)
        )
        self.datageom = self.productInfo["footprint"]
        self.bounds = featureBounds(self.datageom)
        return self

    def _get_asset_url(self, asset: str) -> str:
        """Validate band name and return asset's url."""
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/measurement/{self.scene_params['beam'].lower()}-{asset}.tiff"
