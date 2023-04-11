"""AWS Sentinel 2 readers."""

import json
import os
from collections import OrderedDict
from typing import Any, Dict, Sequence, Type, Union

import attr
from morecantile import TileMatrixSet
from rasterio.crs import CRS
from rasterio.features import bounds as featureBounds

from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import InvalidBandName
from rio_tiler.io import MultiBandReader, Reader
from rio_tiler_pds.sentinel.utils import s2_sceneid_parser
from rio_tiler_pds.utils import fetch

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
        input (str): Sentinel-2 L1C sceneid.

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

    input: str = attr.ib()
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    minzoom: int = attr.ib(default=8)
    maxzoom: int = attr.ib(default=14)

    reader: Type[Reader] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(default={"options": {"nodata": 0}})

    bands: Sequence[str] = attr.ib(init=False, default=default_l1c_bands)

    tileInfo: Dict = attr.ib(init=False)
    datageom: Dict = attr.ib(init=False)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="sentinel-s2-l1c")
    prefix_pattern: str = attr.ib(
        default="tiles/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{_day}/{num}"
    )

    def __attrs_post_init__(self):
        """Fetch productInfo and get bounds."""
        self.scene_params = s2_sceneid_parser(self.input)

        prefix = self.prefix_pattern.format(**self.scene_params)
        self.tileInfo = fetch(
            f"s3://{self.bucket}/{prefix}/tileInfo.json", request_pays=True
        )

        self.datageom = self.tileInfo["tileDataGeometry"]
        self.bounds = featureBounds(self.datageom)
        self.crs = CRS.from_user_input(self.datageom["crs"]["properties"]["name"])

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        band = band if len(band) == 3 else f"B0{band[-1]}"

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid.\nValid bands: {self.bands}")

        prefix = self.prefix_pattern.format(**self.scene_params)
        return f"{self._scheme}://{self.bucket}/{prefix}/{band}.jp2"


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

# STAC < 1.0.0
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

# https://github.com/cogeotiff/rio-tiler-pds/issues/63
# STAC >= 1.0.0
sentinel_l2a_band_map = {
    "B01": "coastal",
    "B02": "blue",
    "B03": "green",
    "B04": "red",
    "B05": "rededge1",
    "B06": "rededge2",
    "B07": "rededge3",
    "B08": "nir",
    "B8A": "nir08",
    "B09": "nir09",
    "B11": "swir16",
    "B12": "swir22",
}


@attr.s
class S2L2AReader(S2L1CReader):
    """AWS Public Dataset Sentinel 2 L2A reader.

    Args:
        input (str): Sentinel-2 L2A sceneid.

    Attributes:
        bands (tuple): list of available bands (default is ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A')).

    Examples:
        >>> with S2L1CReader('S2A_L1C_20170729_19UDP_0') as scene:
                print(scene.bounds)

    """

    bands: Sequence[str] = attr.ib(init=False, default=default_l2a_bands)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="sentinel-s2-l2a")
    prefix_pattern: str = attr.ib(
        default="tiles/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/{_day}/{num}"
    )

    def _get_resolution(self, band: str) -> str:
        """Return L2A resolution prefix"""
        if band.startswith("B"):
            for resolution, bands in SENTINEL_L2_BANDS.items():
                if band in bands:
                    return resolution

        for resolution, bands in SENTINEL_L2_PRODUCTS.items():
            if band in bands:
                return resolution

        raise ValueError(f"Couldn't find resolution for Band {band}")

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        band = band if len(band) == 3 else f"B0{band[-1]}"

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid.\nValid bands: {self.bands}")

        prefix = self.prefix_pattern.format(**self.scene_params)
        res = self._get_resolution(band)
        return f"{self._scheme}://{self.bucket}/{prefix}/R{res}m/{band}.jp2"


@attr.s
class S2L2ACOGReader(MultiBandReader):
    """AWS Public Dataset Sentinel 2 L2A COGS reader.

    Args:
        input (str): Sentinel-2 sceneid.

    Attributes:
        minzoom (int): Dataset's Min Zoom level (default is 8).
        maxzoom (int): Dataset's Max Zoom level (default is 14).
        scene_params (dict): scene id parameters.
        bands (tuple): list of available bands (defined by the STAC item.json).
        stac_item (dict): sentinel 2 COG STAC item content.

    Examples:
        >>> with S2L2ACOGReader('S2A_29RKH_20200219_0_L2A') as scene:
                print(scene.bounds)

    """

    input: str = attr.ib()
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    minzoom: int = attr.ib(default=8)
    maxzoom: int = attr.ib(default=14)

    reader: Type[Reader] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(factory=dict)

    stac_item: Dict = attr.ib(init=False)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="sentinel-cogs")
    prefix_pattern: str = attr.ib(
        default="sentinel-s2-{_levelLow}-cogs/{_utm}/{lat}/{sq}/{acquisitionYear}/{_month}/S{sensor}{satellite}_{_utm}{lat}{sq}_{acquisitionYear}{acquisitionMonth}{acquisitionDay}_{num}_{processingLevel}"
    )

    def __attrs_post_init__(self):
        """Fetch item.json and get bounds and bands."""
        self.scene_params = s2_sceneid_parser(self.input)

        cog_sceneid = "S{sensor}{satellite}_{_utm}{lat}{sq}_{acquisitionYear}{acquisitionMonth}{acquisitionDay}_{num}_{processingLevel}".format(
            **self.scene_params
        )
        prefix = self.prefix_pattern.format(**self.scene_params)
        try:
            self.stac_item = fetch(
                f"https://{self.bucket}.s3.us-west-2.amazonaws.com/{prefix}/{cog_sceneid}.json"
            )

        except:  # noqa
            self.stac_item = fetch(f"s3://{self.bucket}/{prefix}/{cog_sceneid}.json")

        self.bounds = self.stac_item["bbox"]
        self.crs = WGS84_CRS

        if self.stac_item["stac_version"] == "1.0.0-beta.2":
            self.bands = tuple(
                [band for band in default_l2a_bands if band in self.stac_item["assets"]]
            )

        else:
            self.bands = tuple(
                [
                    band
                    for band, name in sentinel_l2a_band_map.items()
                    if name in self.stac_item["assets"]
                ]
            )

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        band = band if len(band) == 3 else f"B0{band[-1]}"

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid.\nValid bands: {self.bands}")

        prefix = self.prefix_pattern.format(**self.scene_params)
        return f"{self._scheme}://{self.bucket}/{prefix}/{band}.tif"


def S2COGReader(sceneid: str, **kwargs: Any) -> S2L2ACOGReader:
    """Sentinel-2 COG readers."""
    scene_params = s2_sceneid_parser(sceneid)
    level = scene_params["processingLevel"]
    if level == "L2A":
        return S2L2ACOGReader(sceneid, **kwargs)
    else:
        raise Exception(f"{level} is not supported")


def S2JP2Reader(sceneid: str, **kwargs: Any) -> Union[S2L2AReader, S2L1CReader]:
    """Sentinel-2 JPEG2000 readers."""
    scene_params = s2_sceneid_parser(sceneid)
    level = scene_params["processingLevel"]
    if level == "L2A":
        return S2L2AReader(sceneid, **kwargs)
    elif level == "L1C":
        return S2L1CReader(sceneid, **kwargs)
    else:
        raise Exception(f"{level} is not supported")
