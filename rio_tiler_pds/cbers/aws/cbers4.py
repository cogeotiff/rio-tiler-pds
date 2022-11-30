"""AWS CBERS 4 reader."""

from typing import Dict, Type

import attr
from morecantile import TileMatrixSet

from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.errors import InvalidBandName
from rio_tiler.io import COGReader, MultiBandReader
from rio_tiler_pds.cbers.utils import sceneid_parser


@attr.s
class CBERSReader(MultiBandReader):
    """AWS Public Dataset CBERS 4 reader.

    Args:
        sceneid (str): CBERS 4 sceneid.

    Attributes:
        scene_params (dict): scene id parameters.
        bands (tuple): list of available bands (default is defined for each sensor).

    Examples:
        >>> with CBERSReader('CBERS_4_AWFI_20170420_146_129_L2') as scene:
                print(scene.bounds)

    """

    input: str = attr.ib()
    reader: Type[COGReader] = attr.ib(default=COGReader)

    reader_options: Dict = attr.ib(factory=dict)
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="cbers-pds")
    prefix_pattern: str = attr.ib(
        default="CBERS{mission}/{instrument}/{path}/{row}/{scene}"
    )

    def __attrs_post_init__(self):
        """Fetch Reference band to get the bounds."""
        self.scene_params = sceneid_parser(self.input)
        self.bands = self.scene_params["bands"]

        ref = self._get_band_url(self.scene_params["reference_band"])
        with self.reader(ref, tms=self.tms, **self.reader_options) as cog:
            self.bounds = cog.bounds
            self.crs = cog.crs
            self.minzoom = cog.minzoom
            self.maxzoom = cog.maxzoom

    def _get_band_url(self, band: str) -> str:
        """Validate band's name and return band's url."""
        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self.prefix_pattern.format(**self.scene_params)
        band = band.replace("B", "BAND")
        return f"{self._scheme}://{self.bucket}/{prefix}/{self.input}_{band}.tif"
