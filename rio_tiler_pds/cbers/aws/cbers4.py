"""AWS CBERS 4 reader."""

from typing import Dict, Type

import attr

from rio_tiler.errors import InvalidBandName
from rio_tiler.io import BaseReader, COGReader, MultiBandReader

from ..utils import sceneid_parser


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

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)

    _scheme: str = "s3"
    _hostname: str = "cbers-pds"
    _prefix: str = "CBERS{mission}/{instrument}/{path}/{row}/{scene}"

    def __attrs_post_init__(self):
        """Fetch Reference band to get the bounds."""
        self.scene_params = sceneid_parser(self.sceneid)
        self.bands = self.scene_params["bands"]

        ref = self._get_band_url(self.scene_params["reference_band"])
        with self.reader(ref, **self.reader_options) as cog:
            self.bounds = cog.bounds
            self.minzoom = cog.minzoom
            self.maxzoom = cog.maxzoom

    def __enter__(self):
        """Support using with Context Managers."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers."""
        pass

    def _get_band_url(self, band: str) -> str:
        """Validate band's name and return band's url."""
        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        band = band.replace("B", "BAND")
        return f"{self._scheme}://{self._hostname}/{prefix}/{self.sceneid}_{band}.tif"
