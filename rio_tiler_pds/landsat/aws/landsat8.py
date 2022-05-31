"""AWS Landsat 8 reader."""

import os
import warnings
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Type, Union

import attr
import numpy
from morecantile import TileMatrixSet
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.io import DatasetReader

from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import (
    ExpressionMixingWarning,
    InvalidBandName,
    MissingBands,
    TileOutsideBounds,
)
from rio_tiler.expression import apply_expression
from rio_tiler.io import COGReader, MultiBandReader
from rio_tiler.models import ImageData
from rio_tiler.tasks import multi_arrays
from rio_tiler.utils import pansharpening_brovey
from rio_tiler_pds.landsat.utils import dn_to_toa, sceneid_parser
from rio_tiler_pds.utils import get_object
from rio_toa import toa_utils

landsat8_valid_bands = (
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B9",
    "B10",
    "B11",
    "BQA",
)


@attr.s
class L8COGReader(COGReader):
    """Custom Landsat COGReader."""

    input: str = attr.ib()
    scene_metadata: Dict = attr.ib()
    dataset: DatasetReader = attr.ib(default=None)

    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib(default=None)
    maxzoom: int = attr.ib(default=None)

    colormap: Dict = attr.ib(default=None)

    # Define global options to be forwarded to functions reading the data (e.g rio_tiler.reader._read)
    nodata: Optional[Union[float, int, str]] = attr.ib(default=None)
    unscale: Optional[bool] = attr.ib(default=None)
    resampling_method: Optional[Resampling] = attr.ib(default=None)
    vrt_options: Optional[Dict] = attr.ib(default=None)
    post_process: Optional[
        Callable[[numpy.ndarray, numpy.ndarray], Tuple[numpy.ndarray, numpy.ndarray]]
    ] = attr.ib(default=None)

    geographic_crs: CRS = attr.ib(init=False, default=WGS84_CRS)

    _kwargs: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def __attrs_post_init__(self):
        """Define _kwargs, open dataset and get info."""
        basename = os.path.basename(self.input)
        band = basename.split(".")[0].split("_")[-1]
        if band == "BQA":
            self.resampling_method = "nearest"
            self.nodata = 1
        else:
            self.nodata = 0

            def post_process(
                arr: numpy.ndarray,
                mask: numpy.ndarray,
            ) -> Tuple[numpy.ndarray, numpy.ndarray]:
                """Post Process function, Apply TOA translation."""
                arr = dn_to_toa(arr, band, self.scene_metadata["L1_METADATA_FILE"])
                return arr, mask

            self.post_process = post_process

        super().__attrs_post_init__()


@attr.s
class L8Reader(MultiBandReader):
    """AWS Public Dataset Landsat 8 reader.

    Args:
        input (str): Landsat 8 sceneid.

    Attributes:
        minzoom (int): Dataset's Min Zoom level (default is 7).
        maxzoom (int): Dataset's Max Zoom level (default is 12).
        scene_params (dict): scene id parameters.
        bands (tuple): list of available bands (default is ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'BQA')).
        mtl_metadata (dict): Landsat 8 MTL document content.

    Examples:
        >>> with S2L1CReader('S2A_L1C_20170729_19UDP_0') as scene:
                print(scene.bounds)

    """

    input: str = attr.ib()
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    reader: Type[L8COGReader] = attr.ib(default=L8COGReader)
    reader_options: Dict = attr.ib(factory=dict)

    minzoom: int = attr.ib(default=7)
    maxzoom: int = attr.ib(default=12)

    mtl_metadata: Dict = attr.ib(init=False)
    bands: Sequence[str] = attr.ib(init=False, default=landsat8_valid_bands)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="landsat-pds")
    prefix_pattern: str = attr.ib(default="c1/L8/{path}/{row}/{scene}")

    def __attrs_post_init__(self):
        """Fetch MTL metadata and get bounds."""
        warnings.warn(
            "L8Reader is deprecated, the landsat-pds bucket will be deleted on July 1st 2021 "
            "(ref: https://lists.osgeo.org/pipermail/landsat-pds/2020-December/000178.html).",
            DeprecationWarning,
        )
        self.scene_params = sceneid_parser(self.input)
        prefix = self.prefix_pattern.format(**self.scene_params)
        basename = f"{self.input}_MTL.txt"
        self.mtl_metadata = toa_utils._parse_mtl_txt(
            get_object(self.bucket, f"{prefix}/{basename}").decode()
        )

        self.bounds = tuple(
            toa_utils._get_bounds_from_metadata(
                self.mtl_metadata["L1_METADATA_FILE"]["PRODUCT_METADATA"]
            )
        )
        self.crs = WGS84_CRS

        self.reader_options.update({"scene_metadata": self.mtl_metadata})

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self.prefix_pattern.format(**self.scene_params)
        return f"{self._scheme}://{self.bucket}/{prefix}/{self.input}_{band}.TIF"

    def tile(
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        bands: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        pan: bool = False,
        **kwargs: Any,
    ) -> ImageData:
        """Read a Mercator Map tile multiple bands."""
        if not self.tile_exists(tile_x, tile_y, tile_z):
            raise TileOutsideBounds(
                f"Tile {tile_z}/{tile_x}/{tile_y} is outside image bounds"
            )

        if isinstance(bands, str):
            bands = (bands,)

        if bands and expression:
            warnings.warn(
                "Both expression and bands passed; expression will overwrite bands parameter.",
                ExpressionMixingWarning,
            )

        if expression:
            bands = self.parse_expression(expression)

        if not bands:
            raise MissingBands(
                "bands must be passed either via expression or bands options."
            )

        if pan:
            bands = tuple(bands) + ("B8",)

        def _reader(band: str, *args: Any, **kwargs: Any) -> ImageData:
            url = self._get_band_url(band)
            with self.reader(url, tms=self.tms, **self.reader_options) as cog:
                data = cog.tile(*args, **kwargs)
                data.band_names = [band]
                return data

        output = multi_arrays(bands, _reader, tile_x, tile_y, tile_z, **kwargs)

        if pan:
            bands = bands[:-1]
            output.data = pansharpening_brovey(
                output.data[:-1], output.data[-1], 0.2, output.data.dtype
            )

        if expression:
            blocks = expression.split(",")
            output.data = apply_expression(blocks, bands, output.data)
            output.band_names = blocks

        return output

    def part(
        self,
        bbox: Tuple[float, float, float, float],
        bands: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        pan: bool = False,
        **kwargs: Any,
    ) -> ImageData:
        """Read part of multiple bands."""
        if isinstance(bands, str):
            bands = (bands,)

        if bands and expression:
            warnings.warn(
                "Both expression and bands passed; expression will overwrite bands parameter.",
                ExpressionMixingWarning,
            )

        if expression:
            bands = self.parse_expression(expression)

        if not bands:
            raise MissingBands(
                "bands must be passed either via expression or bands options."
            )

        if pan:
            bands = tuple(bands) + ("B8",)

        def _reader(band: str, *args: Any, **kwargs: Any) -> ImageData:
            url = self._get_band_url(band)
            with self.reader(url, tms=self.tms, **self.reader_options) as cog:
                data = cog.part(*args, **kwargs)
                data.band_names = [band]
                return data

        output = multi_arrays(bands, _reader, bbox, **kwargs)

        if pan:
            bands = bands[:-1]
            output.data = pansharpening_brovey(
                output.data[:-1], output.data[-1], 0.2, output.data.dtype
            )

        if expression:
            blocks = expression.split(",")
            output.data = apply_expression(blocks, bands, output.data)
            output.band_names = blocks

        return output

    def preview(
        self,
        bands: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        pan: bool = False,
        **kwargs: Any,
    ) -> ImageData:
        """Return a preview from multiple bands."""
        if isinstance(bands, str):
            bands = (bands,)

        if bands and expression:
            warnings.warn(
                "Both expression and bands passed; expression will overwrite bands parameter.",
                ExpressionMixingWarning,
            )

        if expression:
            bands = self.parse_expression(expression)

        if not bands:
            raise MissingBands(
                "bands must be passed either via expression or bands options."
            )

        if pan:
            bands = tuple(bands) + ("B8",)

        def _reader(band: str, **kwargs: Any) -> ImageData:
            url = self._get_band_url(band)
            with self.reader(url, tms=self.tms, **self.reader_options) as cog:
                data = cog.preview(**kwargs)
                data.band_names = [band]
                return data

        output = multi_arrays(bands, _reader, **kwargs)

        if pan:
            bands = bands[:-1]
            output.data = pansharpening_brovey(
                output.data[:-1], output.data[-1], 0.2, output.data.dtype
            )

        if expression:
            blocks = expression.split(",")
            output.data = apply_expression(blocks, bands, output.data)
            output.band_names = blocks

        return output

    def feature(
        self,
        shape: Dict,
        bands: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        pan: bool = False,
        **kwargs: Any,
    ) -> ImageData:
        """Read multiple bands for a GeoJSON feature."""
        if isinstance(bands, str):
            bands = (bands,)

        if bands and expression:
            warnings.warn(
                "Both expression and bands passed; expression will overwrite bands parameter.",
                ExpressionMixingWarning,
            )

        if expression:
            bands = self.parse_expression(expression)

        if not bands:
            raise MissingBands(
                "bands must be passed either via expression or bands options."
            )

        if pan:
            bands = tuple(bands) + ("B8",)

        def _reader(band: str, *args: Any, **kwargs: Any) -> ImageData:
            url = self._get_band_url(band)
            with self.reader(url, tms=self.tms, **self.reader_options) as cog:
                data = cog.feature(*args, **kwargs)
                data.band_names = [band]
                return data

        output = multi_arrays(bands, _reader, shape, **kwargs)

        if pan:
            bands = bands[:-1]
            output.data = pansharpening_brovey(
                output.data[:-1], output.data[-1], 0.2, output.data.dtype
            )

        if expression:
            blocks = expression.split(",")
            output.data = apply_expression(blocks, bands, output.data)

        return output
