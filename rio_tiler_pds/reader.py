"""MultiBand reader."""

import warnings
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import attr
import rasterio
from rasterio import transform
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

from rio_tiler import constants
from rio_tiler.errors import ExpressionMixingWarning, MissingAssets
from rio_tiler.expression import apply_expression
from rio_tiler.io import COGReader, MultiBaseReader
from rio_tiler.tasks import multi_values
from rio_tiler.utils import aws_get_object


@lru_cache(maxsize=512)
def get_object(bucket: str, key: str, request_pays: bool = False) -> bytes:
    """Add LRU cache on top of AWS Get Object."""
    return aws_get_object(bucket, key, request_pays=request_pays)


@attr.s
class MultiBandReader(MultiBaseReader):
    """Multi Band Reader.

    Attributes:
        bounds (tuple): Dataset's bounds.
        minzoom (int): Dataset's Min Zoom level.
        maxzoom (int): Dataset's Max Zoom level.

    """

    minzoom: int = attr.ib(init=False)
    maxzoom: int = attr.ib(init=False)

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
        self, assets: Union[Sequence[str], str] = None, *args, **kwargs: Any
    ) -> Dict:
        """Return metadata from multiple assets"""
        if not assets:
            raise MissingAssets("Missing 'assets' option")

        if isinstance(assets, str):
            assets = (assets,)

        def _reader(asset: str, **kwargs: Any) -> Dict:
            url = self._get_asset_url(asset)
            with self.reader(url, **self.reader_options) as cog:
                return cog.info()

        bands_metadata = multi_values(assets, _reader, *args, **kwargs)
        meta = self.spatial_info
        meta["band_metadata"] = [
            (ix + 1, bands_metadata[asset]["band_metadata"][0][1])
            for ix, asset in enumerate(assets)
        ]
        meta["band_descriptions"] = [(ix + 1, asset) for ix, asset in enumerate(assets)]
        meta["dtype"] = bands_metadata[assets[0]]["dtype"]
        meta["colorinterp"] = [
            bands_metadata[asset]["colorinterp"][0] for _, asset in enumerate(assets)
        ]
        meta["nodata_type"] = bands_metadata[assets[0]]["nodata_type"]
        return meta

    def stats(
        self,
        pmin: float = 2.0,
        pmax: float = 98.0,
        hist_options: Optional[Dict] = None,
        assets: Union[Sequence[str], str] = None,
        **kwargs: Any,
    ) -> Dict:
        """Return array statistics from multiple assets"""
        if not assets:
            raise MissingAssets("Missing 'assets' option")

        if isinstance(assets, str):
            assets = (assets,)

        def _reader(asset: str, *args, **kwargs) -> Dict:
            url = self._get_asset_url(asset)
            with self.reader(url, **self.reader_options) as cog:
                return cog.stats(*args, **kwargs)[1]

        return multi_values(
            assets, _reader, pmin, pmax, hist_options=hist_options, *kwargs,
        )

    def metadata(
        self,
        pmin: float = 2.0,
        pmax: float = 98.0,
        assets: Union[Sequence[str], str] = None,
        **kwargs: Any,
    ) -> Dict:
        """Return metadata from multiple assets"""
        if not assets:
            raise MissingAssets("Missing 'assets' option")

        if isinstance(assets, str):
            assets = (assets,)

        def _reader(asset: str, *args, **kwargs) -> Dict:
            url = self._get_asset_url(asset)
            with self.reader(url, **self.reader_options) as cog:
                meta = cog.metadata(*args, **kwargs)
                meta["statistics"] = meta["statistics"][1]
                return meta

        bands_metadata = multi_values(assets, _reader, pmin, pmax, **kwargs)

        meta = self.spatial_info
        meta["band_metadata"] = [
            (ix + 1, bands_metadata[asset]["band_metadata"][0][1])
            for ix, asset in enumerate(assets)
        ]
        meta["band_descriptions"] = [(ix + 1, asset) for ix, asset in enumerate(assets)]
        meta["dtype"] = bands_metadata[assets[0]]["dtype"]
        meta["colorinterp"] = [
            bands_metadata[asset]["colorinterp"][0] for _, asset in enumerate(assets)
        ]
        meta["nodata_type"] = bands_metadata[assets[0]]["nodata_type"]
        meta["statistics"] = {
            asset: bands_metadata[asset]["statistics"] for _, asset in enumerate(assets)
        }
        return meta

    def point(
        self,
        lon: float,
        lat: float,
        assets: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        asset_expression: Optional[
            str
        ] = "",  # Expression for each asset based on index names
        **kwargs: Any,
    ) -> List:
        """Read a pixel values from multiple assets,"""
        if isinstance(assets, str):
            assets = (assets,)

        if assets and expression:
            warnings.warn(
                "Both expression and assets passed; expression will overwrite assets parameter.",
                ExpressionMixingWarning,
            )

        if expression:
            assets = self.parse_expression(expression)

        if not assets:
            raise MissingAssets(
                "assets must be passed either via expression or assets options."
            )

        def _reader(asset: str, *args, **kwargs: Any) -> Dict:
            url = self._get_asset_url(asset)
            with self.reader(url, **self.reader_options) as cog:  # type: ignore
                return cog.point(*args, **kwargs)[0]  # We only return the firt value

        data = multi_values(
            assets, _reader, lon, lat, expression=asset_expression, **kwargs,
        )

        values = [d for _, d in data.items()]
        if expression:
            blocks = expression.split(",")
            values = apply_expression(blocks, assets, values).tolist()

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
