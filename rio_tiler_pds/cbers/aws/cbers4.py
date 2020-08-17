"""rio_tiler.cbers: cbers processing."""

from typing import Dict, Type

import attr

from rio_tiler.errors import InvalidAssetName
from rio_tiler.io import BaseReader, COGReader

from ...reader import MultiBandReader
from ..utils import cbers_parser


@attr.s
class CBERSReader(MultiBandReader):
    """AWS Public Dataset CBERS 4 reader."""

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)

    _scheme: str = "s3"
    _hostname: str = "cbers-pds"
    _prefix: str = "CBERS4/{instrument}/{path}/{row}/{scene}"

    def __enter__(self):
        """Support using with Context Managers."""
        self.scene_params = cbers_parser(self.sceneid)
        self.assets = self.scene_params["bands"]

        ref = self._get_asset_url(self.scene_params["reference_band"])
        # TODO: Should be cached
        with self.reader(ref, **self.reader_options) as cog:
            self.bounds = cog.bounds
            self.minzoom = cog.minzoom
            self.maxzoom = cog.maxzoom

        return self

    def _get_asset_url(self, asset: str) -> str:
        """Validate band name and return asset's url."""
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        asset = asset.replace("B", "BAND")
        return f"{self._scheme}://{self._hostname}/{prefix}/{self.sceneid}_{asset}.tif"
