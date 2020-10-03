"""AWS Landsat 8 reader."""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

import attr
import numpy
from rio_toa import toa_utils

from rio_tiler.errors import InvalidBandName, MissingBands
from rio_tiler.expression import apply_expression
from rio_tiler.io import BaseReader, COGReader, MultiBandReader
from rio_tiler.tasks import multi_arrays, multi_values
from rio_tiler.utils import pansharpening_brovey

from ... import get_object
from ..utils import dn_to_toa, sceneid_parser

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
class L8Reader(MultiBandReader):
    """AWS Public Dataset Landsat 8 reader.

    Args:
        sceneid (str): Landsat 8 sceneid.

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

    sceneid: str = attr.ib()
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)
    minzoom: int = attr.ib(init=False, default=7)
    maxzoom: int = attr.ib(init=False, default=12)

    mtl_metadata: Dict = attr.ib(init=False)
    bands: Tuple = attr.ib(init=False, default=landsat8_valid_bands)

    _scheme: str = "s3"
    _hostname: str = "landsat-pds"
    _prefix: str = "c1/L8/{path}/{row}/{scene}"

    def __attrs_post_init__(self):
        """Fetch MTL metadata and get bounds."""
        self.scene_params = sceneid_parser(self.sceneid)
        prefix = self._prefix.format(**self.scene_params)
        basename = f"{self.sceneid}_MTL.txt"
        self.mtl_metadata = toa_utils._parse_mtl_txt(
            get_object(self._hostname, f"{prefix}/{basename}").decode()
        )
        self.bounds = tuple(
            toa_utils._get_bounds_from_metadata(
                self.mtl_metadata["L1_METADATA_FILE"]["PRODUCT_METADATA"]
            )
        )

    def __enter__(self):
        """Support using with Context Managers."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers."""
        pass

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/{self.sceneid}_{band}.TIF"

    def _convert_stats(self, statistics: Dict, band: str):
        statistics["pc"] = dn_to_toa(
            numpy.array(statistics["pc"]), band, self.mtl_metadata["L1_METADATA_FILE"]
        ).tolist()

        statistics["min"] = dn_to_toa(
            numpy.array([statistics["min"]]),
            band,
            self.mtl_metadata["L1_METADATA_FILE"],
        )[0]

        statistics["max"] = dn_to_toa(
            numpy.array([statistics["max"]]),
            band,
            self.mtl_metadata["L1_METADATA_FILE"],
        )[0]

        statistics["std"] = dn_to_toa(
            numpy.array([statistics["std"]]),
            band,
            self.mtl_metadata["L1_METADATA_FILE"],
        )[0]

        statistics["histogram"][1] = dn_to_toa(
            numpy.array(statistics["histogram"][1]),
            band,
            self.mtl_metadata["L1_METADATA_FILE"],
        ).tolist()
        return statistics

    def stats(
        self,
        pmin: float = 2.0,
        pmax: float = 98.0,
        hist_options: Optional[Dict] = None,
        bands: Union[Sequence[str], str] = None,
        **kwargs: Any,
    ) -> Dict:
        """Return array statistics from multiple bands"""
        if not bands:
            raise MissingBands("Missing 'bands' option")

        if isinstance(bands, str):
            bands = (bands,)

        def _reader(band: str, *args, **kwargs) -> Dict:
            url = self._get_band_url(band)
            nodata = 0
            if band == "BQA":
                nodata = 1
                kwargs["resampling_method"] = "nearest"
            kwargs.update({"nodata": nodata})
            with self.reader(url, **self.reader_options) as cog:
                result = cog.stats(*args, **kwargs)[1]
                return self._convert_stats(result, band)

        return multi_values(
            bands, _reader, pmin, pmax, hist_options=hist_options, **kwargs,
        )

    def metadata(
        self,
        pmin: float = 2.0,
        pmax: float = 98.0,
        bands: Union[Sequence[str], str] = None,
        **kwargs: Any,
    ) -> Dict:
        """Return metadata from multiple bands"""
        if not bands:
            raise MissingBands("Missing 'bands' option")

        if isinstance(bands, str):
            bands = (bands,)

        def _reader(band: str, *args, **kwargs) -> Dict:
            url = self._get_band_url(band)
            nodata = 0
            if band == "BQA":
                nodata = 1
                kwargs["resampling_method"] = "nearest"
            kwargs.update({"nodata": nodata})
            with self.reader(url, **self.reader_options) as cog:
                metadata = cog.metadata(*args, **kwargs)
                metadata["statistics"] = self._convert_stats(
                    metadata["statistics"][1], band
                )
                return metadata

        bands_metadata = multi_values(bands, _reader, pmin, pmax, **kwargs)
        meta = self.spatial_info
        meta["band_metadata"] = [
            (ix + 1, bands_metadata[band]["band_metadata"][0][1])
            for ix, band in enumerate(bands)
        ]
        meta["band_descriptions"] = [(ix + 1, band) for ix, band in enumerate(bands)]
        meta["dtype"] = bands_metadata[bands[0]]["dtype"]
        meta["colorinterp"] = [
            bands_metadata[band]["colorinterp"][0] for _, band in enumerate(bands)
        ]
        meta["nodata_type"] = bands_metadata[bands[0]]["nodata_type"]
        meta["statistics"] = {
            band: bands_metadata[band]["statistics"] for _, band in enumerate(bands)
        }
        return meta

    def tile(
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        bands: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        band_expression: Optional[
            str
        ] = "",  # Expression for each band based on index names
        pan: bool = False,
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read a Mercator Map tile multiple bands."""
        if isinstance(bands, str):
            bands = (bands,)

        if expression:
            bands = self.parse_expression(expression)

        if not bands:
            raise MissingBands(
                "bands must be passed either via expression or bands options."
            )

        if pan:
            bands = tuple(bands) + ("B8",)

        def _reader(
            band: str, *args: Any, **kwargs: Any
        ) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_band_url(band)
            nodata = 0
            if band == "BQA":
                nodata = 1
                kwargs["resampling_method"] = "nearest"
            kwargs.update({"nodata": nodata})
            with self.reader(url, **self.reader_options) as cog:
                tile, mask = cog.tile(*args, **kwargs)
                tile = dn_to_toa(tile, band, self.mtl_metadata["L1_METADATA_FILE"])
            return tile, mask

        data, mask = multi_arrays(
            bands,
            _reader,
            tile_x,
            tile_y,
            tile_z,
            expression=band_expression,
            **kwargs,
        )

        if pan:
            bands = bands[:-1]
            data = pansharpening_brovey(data[:-1], data[-1], 0.2, data.dtype)

        if expression:
            blocks = expression.split(",")
            data = apply_expression(blocks, bands, data)

        return data, mask

    def part(
        self,
        bbox: Tuple[float, float, float, float],
        bands: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        band_expression: Optional[
            str
        ] = "",  # Expression for each band based on index names
        pan: bool = False,
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read part of multiple bands."""
        if isinstance(bands, str):
            bands = (bands,)

        if expression:
            bands = self.parse_expression(expression)

        if not bands:
            raise MissingBands(
                "bands must be passed either via expression or bands options."
            )

        if pan:
            bands = tuple(bands) + ("B8",)

        def _reader(
            band: str, *args: Any, **kwargs: Any
        ) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_band_url(band)
            nodata = 0
            if band == "BQA":
                nodata = 1
                kwargs["resampling_method"] = "nearest"
            kwargs.update({"nodata": nodata})
            with self.reader(url, **self.reader_options) as cog:
                data, mask = cog.part(*args, **kwargs)
                data = dn_to_toa(data, band, self.mtl_metadata["L1_METADATA_FILE"])
            return data, mask

        data, mask = multi_arrays(
            bands, _reader, bbox, expression=band_expression, **kwargs,
        )

        if pan:
            bands = bands[:-1]
            data = pansharpening_brovey(data[:-1], data[-1], 0.2, data.dtype)

        if expression:
            blocks = expression.split(",")
            data = apply_expression(blocks, bands, data)

        return data, mask

    def preview(
        self,
        bands: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        band_expression: Optional[
            str
        ] = "",  # Expression for each band based on index names
        pan: bool = False,
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Return a preview from multiple bands."""
        if isinstance(bands, str):
            bands = (bands,)

        if expression:
            bands = self.parse_expression(expression)

        if not bands:
            raise MissingBands(
                "bands must be passed either via expression or bands options."
            )

        if pan:
            bands = tuple(bands) + ("B8",)

        def _reader(band: str, **kwargs: Any) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_band_url(band)
            nodata = 0
            if band == "BQA":
                nodata = 1
                kwargs["resampling_method"] = "nearest"
            kwargs.update({"nodata": nodata})
            with self.reader(url, **self.reader_options) as cog:
                data, mask = cog.preview(**kwargs)
                data = dn_to_toa(data, band, self.mtl_metadata["L1_METADATA_FILE"])
            return data, mask

        data, mask = multi_arrays(bands, _reader, expression=band_expression, **kwargs)

        if pan:
            bands = bands[:-1]
            data = pansharpening_brovey(data[:-1], data[-1], 0.2, data.dtype)

        if expression:
            blocks = expression.split(",")
            data = apply_expression(blocks, bands, data)

        return data, mask

    def point(
        self,
        lon: float,
        lat: float,
        bands: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        band_expression: Optional[
            str
        ] = "",  # Expression for each band based on index names
        **kwargs: Any,
    ) -> List:
        """Read a value from COGs."""
        if isinstance(bands, str):
            bands = (bands,)

        if expression:
            bands = self.parse_expression(expression)

        if not bands:
            raise MissingBands(
                "bands must be passed either via expression or bands options."
            )

        def _reader(band: str, *args, **kwargs: Any) -> Dict:
            url = self._get_band_url(band)
            nodata = 1 if band == "BQA" else 0
            kwargs.update({"nodata": nodata})
            with self.reader(url, **self.reader_options) as cog:
                data = numpy.array(cog.point(*args, **kwargs))
                data = dn_to_toa(data, band, self.mtl_metadata["L1_METADATA_FILE"])
            return data.tolist()[0]

        data = multi_values(
            bands, _reader, lon, lat, expression=band_expression, **kwargs,
        )

        values = [d for _, d in data.items()]
        if expression:
            blocks = expression.split(",")
            values = apply_expression(blocks, bands, values).tolist()

        return values
