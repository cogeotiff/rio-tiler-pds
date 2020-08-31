"""MultiBand reader."""

import abc
import re
import warnings
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

import attr
import numpy
import rasterio
from rasterio import transform
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

from rio_tiler import constants
from rio_tiler.errors import ExpressionMixingWarning
from rio_tiler.expression import apply_expression
from rio_tiler.io import BaseReader, COGReader
from rio_tiler.tasks import multi_arrays, multi_values
from rio_tiler.utils import aws_get_object

from .errors import MissingBands


@lru_cache(maxsize=512)
def get_object(bucket: str, key: str, request_pays: bool = False) -> bytes:
    """Add LRU cache on top of AWS Get Object."""
    return aws_get_object(bucket, key, request_pays=request_pays)


@attr.s
class MultiBandReader(BaseReader, metaclass=abc.ABCMeta):
    """Multi Band Reader.

    Attributes:
        bounds (tuple): Dataset's bounds.
        minzoom (int): Dataset's Min Zoom level.
        maxzoom (int): Dataset's Max Zoom level.

    """

    reader: Type[BaseReader] = attr.ib()
    reader_options: Dict = attr.ib(factory=dict)
    bounds: Tuple[float, float, float, float] = attr.ib(init=False)
    bands: Sequence[str] = attr.ib(init=False)
    minzoom: int = attr.ib(init=False)
    maxzoom: int = attr.ib(init=False)

    @abc.abstractmethod
    def __enter__(self):
        """Support using with Context Managers."""
        ...

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers."""
        pass

    @abc.abstractmethod
    def _get_band_url(self, band: str) -> str:
        """Validate band name and construct url."""
        ...

    def parse_expression(self, expression: str) -> Tuple:
        """Parse rio-tiler band math expression."""
        bands = "|".join([fr"\b{band}\b" for band in self.bands])
        _re = re.compile(bands.replace("\\\\", "\\"))
        return tuple(set(re.findall(_re, expression)))

    @property
    def center(self) -> Tuple[float, float, int]:
        """Dataset center + minzoom."""
        return (
            (self.bounds[0] + self.bounds[2]) / 2,
            (self.bounds[1] + self.bounds[3]) / 2,
            self.minzoom,
        )

    @property
    def spatial_info(self) -> Dict:
        """Dataset's spatial info (bounds, center and zooms)."""
        return {
            "bounds": self.bounds,
            "center": self.center,
            "minzoom": self.minzoom,
            "maxzoom": self.maxzoom,
        }

    def info(
        self, bands: Union[Sequence[str], str] = None, *args, **kwargs: Any
    ) -> Dict:
        """Return metadata from multiple bands"""
        if not bands:
            raise MissingBands("Missing 'bands' option")

        if isinstance(bands, str):
            bands = (bands,)

        def _reader(band: str, **kwargs: Any) -> Dict:
            url = self._get_band_url(band)
            with self.reader(url, **self.reader_options) as cog:
                return cog.info()

        bands_metadata = multi_values(bands, _reader, *args, **kwargs)
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
        return meta

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
            with self.reader(url, **self.reader_options) as cog:
                return cog.stats(*args, **kwargs)[1]

        return multi_values(
            bands, _reader, pmin, pmax, hist_options=hist_options, *kwargs,
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
            with self.reader(url, **self.reader_options) as cog:
                meta = cog.metadata(*args, **kwargs)
                meta["statistics"] = meta["statistics"][1]
                return meta

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
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read a Mercator Map tile multiple bands."""
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

        def _reader(
            band: str, *args: Any, **kwargs: Any
        ) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_band_url(band)
            with self.reader(url, **self.reader_options) as cog:
                return cog.tile(*args, **kwargs)

        data, mask = multi_arrays(
            bands,
            _reader,
            tile_x,
            tile_y,
            tile_z,
            expression=band_expression,
            **kwargs,
        )

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
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
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

        def _reader(
            band: str, *args: Any, **kwargs: Any
        ) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_band_url(band)
            with self.reader(url, **self.reader_options) as cog:  # type: ignore
                return cog.part(*args, **kwargs)

        data, mask = multi_arrays(
            bands, _reader, bbox, expression=band_expression, **kwargs,
        )

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
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
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

        def _reader(band: str, **kwargs: Any) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_band_url(band)
            with self.reader(url, **self.reader_options) as cog:  # type: ignore
                return cog.preview(**kwargs)

        data, mask = multi_arrays(bands, _reader, expression=band_expression, **kwargs)

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
        ] = "",  # Expression for each band based on index names (b1, b2, ...)
        **kwargs: Any,
    ) -> List:
        """Read a pixel values from multiple bands,"""
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

        def _reader(band: str, *args, **kwargs: Any) -> Dict:
            url = self._get_band_url(band)
            with self.reader(url, **self.reader_options) as cog:  # type: ignore
                return cog.point(*args, **kwargs)[0]  # We only return the firt value

        data = multi_values(
            bands, _reader, lon, lat, expression=band_expression, **kwargs,
        )

        values = [d for _, d in data.items()]
        if expression:
            blocks = expression.split(",")
            values = apply_expression(blocks, bands, values).tolist()

        return values


@attr.s
class GCPCOGReader(COGReader):
    """Custom COG Reader with GCPS support.

    Attributes:
        src_dataset (DatasetReader): rasterio openned dataset.
        dataset (WarpedVRT): rasterio WarpedVRT dataset.

    """

    def __enter__(self):
        """Open rasterio datasets."""
        self.src_dataset = rasterio.open(self.filepath)
        self.dataset = WarpedVRT(
            self.src_dataset,
            src_crs=self.src_dataset.gcps[1],
            src_transform=transform.from_gcps(self.src_dataset.gcps[0]),
            src_nodata=0,
        )

        self.bounds = transform_bounds(
            self.dataset.crs, constants.WGS84_CRS, *self.dataset.bounds, densify_pts=21
        )

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close rasterio datasets."""
        self.dataset.close()
        self.src_dataset.close()
