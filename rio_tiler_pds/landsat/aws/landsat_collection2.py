"""AWS Landsat Collection 2 reader.

Notes:
  - For collection 2, level 2, ETM and TM have the same bands
  - There is no level 2 for MSS sensor
  - processing_level for level 2 are `L2SR` or `L2SP`
  -  The L2SR includes:
    - Surface Reflectance (SR)
    - angle coefficients file,
    - Quality Assessment (QA) Bands
  - The L2SP includes
    - Surface Reflectance (SR)
    - Surface Temperature (ST)
    - ST intermediate bands
    - angle coefficients file
    - Quality Assessment (QA) Band.

Links:
  - https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2

"""

import json
from typing import Dict, Type

import attr
from botocore.exceptions import ClientError
from morecantile import TileMatrixSet

from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import InvalidBandName
from rio_tiler.io import COGReader, MultiBandReader
from rio_tiler_pds.landsat.utils import sceneid_parser
from rio_tiler_pds.utils import get_object


@attr.s
class LandsatC2Reader(MultiBandReader):
    """AWS Public Dataset Landsat Collection 2 COG Reader.

    Args:
        input (str): Landsat 8 sceneid.

    Attributes:
        minzoom (int): Dataset's Min Zoom level (default is 5).
        maxzoom (int): Dataset's Max Zoom level (default is 12).
        scene_params (dict): scene id parameters.
        bands (tuple): list of available bands.

    Examples:
        >>> with LandsatC2Reader('LC08_L2SR_093106_20200207_20201016_02_T2') as scene:
                print(scene.bounds)

        >>> with LandsatC2Reader('LC08_L1TP_116043_20201122_20201122_02_RT') as scene:
                print(scene.bounds)

    """

    input: str = attr.ib()
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    reader: Type[COGReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)

    minzoom: int = attr.ib(default=5)
    maxzoom: int = attr.ib(default=12)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="usgs-landsat")
    prefix_pattern: str = attr.ib(
        default="collection02/level-{_processingLevelNum}/{category}/{_sensor_s3_prefix}/{acquisitionYear}/{path}/{row}/{scene}/{scene}"
    )

    def __attrs_post_init__(self):
        """Fetch productInfo and get bounds."""
        self.scene_params = sceneid_parser(self.input)
        self.bands = self.scene_params["bands"]

        self.bounds = self.get_geometry()
        self.crs = WGS84_CRS

    def get_geometry(self):
        """Fetch geometry info for the scene."""
        # Allow custom function for users who want to use the WRS2 grid and
        # avoid this GET request.
        prefix = self.prefix_pattern.format(**self.scene_params)

        if self.scene_params["_processingLevelNum"] == "1":
            stac_key = f"{prefix}_stac.json"
        else:
            # This fetches the Surface Reflectance (SR) STAC item.
            # There are separate STAC items for Surface Reflectance and Surface
            # Temperature (ST), but they have the same geometry. The SR should
            # always exist, the ST might not exist based on the scene.
            stac_key = f"{prefix}_SR_stac.json"

        try:
            self.stac_item = json.loads(
                get_object(self.bucket, stac_key, request_pays=True)
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ValueError(
                    "stac_item not found. Some RT scenes may not exist in usgs-landsat bucket."
                )
            else:
                raise e

        return self.stac_item["bbox"]

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        # TODO: allow B1 instead of SR_B1

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid.\nValid bands: {self.bands}")

        prefix = self.prefix_pattern.format(**self.scene_params)
        return f"{self._scheme}://{self.bucket}/{prefix}_{band}.TIF"
