"""rio_tiler.cbers: cbers processing."""

import attr
import re
from typing import Any, Dict, Type

from rio_tiler.io import BaseReader, COGReader
from rio_tiler.errors import InvalidAssetName

from ..errors import InvalidCBERSSceneId
from ..reader import MultiBandReader


def cbers_parser(sceneid: str) -> Dict:
    """Parse CBERS scene id.

    Attributes
    ----------
        sceneid : str
            CBERS sceneid.

    Returns
    -------
        out : dict
            dictionary with metadata constructed from the sceneid.

    """
    if not re.match(r"^CBERS_4_\w+_[0-9]{8}_[0-9]{3}_[0-9]{3}_L[0-9]$", sceneid):
        raise InvalidCBERSSceneId("Could not match {}".format(sceneid))

    cbers_pattern = (
        r"(?P<satellite>\w+)_"
        r"(?P<mission>[0-9]{1})"
        r"_"
        r"(?P<instrument>\w+)"
        r"_"
        r"(?P<acquisitionYear>[0-9]{4})"
        r"(?P<acquisitionMonth>[0-9]{2})"
        r"(?P<acquisitionDay>[0-9]{2})"
        r"_"
        r"(?P<path>[0-9]{3})"
        r"_"
        r"(?P<row>[0-9]{3})"
        r"_"
        r"(?P<processingCorrectionLevel>L[0-9]{1})$"
    )

    meta: Dict[str, Any] = re.match(cbers_pattern, sceneid, re.IGNORECASE).groupdict()
    meta["scene"] = sceneid
    meta["date"] = "{}-{}-{}".format(
        meta["acquisitionYear"], meta["acquisitionMonth"], meta["acquisitionDay"]
    )

    instrument = meta["instrument"]
    instrument_params = {
        "MUX": {
            "reference_band": "B6",
            "bands": ("B5", "B6", "B7", "B8"),
            "rgb": ("B7", "B6", "B5"),
        },
        "AWFI": {
            "reference_band": "B14",
            "bands": ("B13", "B14", "B15", "B16"),
            "rgb": ("B15", "B14", "B13"),
        },
        "PAN10M": {
            "reference_band": "B4",
            "bands": ("B2", "B3", "B4"),
            "rgb": ("B3", "B4", "B2"),
        },
        "PAN5M": {"reference_band": "B1", "bands": ("B1"), "rgb": ("B1", "B1", "B1")},
    }
    meta["reference_band"] = instrument_params[instrument]["reference_band"]
    meta["bands"] = instrument_params[instrument]["bands"]
    meta["rgb"] = instrument_params[instrument]["rgb"]

    return meta


@attr.s
class AWSPDS_CBERSReader(MultiBandReader):
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
