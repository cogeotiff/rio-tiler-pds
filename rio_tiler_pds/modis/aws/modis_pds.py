"""AWS MODIS reader."""

from typing import Dict, Type

import attr
from morecantile import TileMatrixSet

from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import InvalidBandName
from rio_tiler.io import COGReader, MultiBandReader
from rio_tiler_pds.errors import InvalidMODISProduct
from rio_tiler_pds.modis.modland_grid import tile_bbox
from rio_tiler_pds.modis.utils import sceneid_parser

MCD43A4_BANDS = (
    "B01",
    "B01qa",
    "B02",
    "B02qa",
    "B03",
    "B03qa",
    "B04",
    "B04qa",
    "B05",
    "B05qa",
    "B06",
    "B06qa",
    "B07",
    "B07qa",
)
MOD09GQ_MYD09GQ_BANDS = (
    "B01",
    "B02",
    "granule",
    "numobs",
    "obscov",
    "obsnum",
    "orbit",
    "qc",
)
MOD09GA_MYD09GA_BAND = (
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "geoflags",
    "granule",
    "numobs1km",
    "numobs500m",
    "obscov",
    "obsnum",
    "orbit",
    "qc500m",
    "qscan",
    "range",
    "senaz",
    "senzen",
    "solaz",
    "solzen",
    "state",
)

modis_valid_bands = {
    "MCD43A4": MCD43A4_BANDS,
    "MOD09GQ": MOD09GQ_MYD09GQ_BANDS,
    "MYD09GQ": MOD09GQ_MYD09GQ_BANDS,
    "MOD09GA": MOD09GA_MYD09GA_BAND,
    "MYD09GA": MOD09GA_MYD09GA_BAND,
}


@attr.s
class MODISReader(MultiBandReader):
    """AWS Public Dataset MODIS reader.

    Args:
        sceneid (str): MODIS sceneid.

    Attributes:
        scene_params (dict): scene id parameters.
        bands (tuple): list of available bands (default is defined for each sensor).

    Examples:
        >>> with MODISReader('MCD43A4.A2017006.h21v11.006.2017018074804') as scene:
                print(scene.bounds)

    """

    input: str = attr.ib()
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    reader: Type[COGReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)

    minzoom: int = attr.ib(default=4)
    # Most of MODIS product are at 500m resolution (zoom = 8)
    # Some are at 250m (zoom = 10) (MOD09GQ & MYD09GQ) thus we use maxzoom = 9 by default
    maxzoom: int = attr.ib(default=9)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="modis-pds")
    prefix_pattern: str = attr.ib(
        default="{product}.{version}/{horizontal_grid}/{vertical_grid}/{date}"
    )

    def __attrs_post_init__(self):
        """Parse Sceneid and get grid bounds."""
        self.scene_params = sceneid_parser(self.input)
        product = self.scene_params["product"]

        if product not in modis_valid_bands:
            raise InvalidMODISProduct(f"{product} is not supported.")

        self.bands = modis_valid_bands[product]
        self.bounds = tile_bbox(
            self.scene_params["horizontal_grid"],
            self.scene_params["vertical_grid"],
        )
        self.crs = WGS84_CRS

    def _get_band_url(self, band: str) -> str:
        """Validate band's name and return band's url."""
        band = f"B0{band[-1]}" if band.startswith("B") and len(band) < 3 else band

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self.prefix_pattern.format(**self.scene_params)
        return f"{self._scheme}://{self.bucket}/{prefix}/{self.input}_{band}.TIF"
