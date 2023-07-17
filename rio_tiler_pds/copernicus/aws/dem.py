"""Copernicus DEM Mosaic Reader.

https://registry.opendata.aws/copernicus-dem/
"""

import json
import math
from typing import Any, Dict, List, Optional, Tuple, Type

import attr
from morecantile import TileMatrixSet
from rasterio.crs import CRS
from rasterio.errors import RasterioIOError
from rasterio.warp import transform as transform_coords
from rasterio.warp import transform_bounds

from rio_tiler.constants import MAX_THREADS, WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import PointOutsideBounds, TileOutsideBounds
from rio_tiler.io import BaseReader, Reader
from rio_tiler.models import BandStatistics, ImageData, Info, PointData
from rio_tiler.mosaic import mosaic_point_reader, mosaic_reader
from rio_tiler.types import BBox


@attr.s
class Dem30Reader(BaseReader):
    """Simple Mosaic reader for copernicus DEM"""

    input: str = attr.ib(default="copernicus-dem-30m")

    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    minzoom: int = attr.ib(default=7)
    maxzoom: int = attr.ib(default=8)

    bounds: BBox = attr.ib(init=False, default=(-180, -90, 180, 90))
    crs: CRS = attr.ib(init=False, default=WGS84_CRS)

    reader: Type[Reader] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(factory=dict)

    colormap: Dict = attr.ib(init=False, factory=dict)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="copernicus-dem-30m")
    prefix_pattern: str = attr.ib(
        default="Copernicus_DSM_COG_10_{northsouth}{lat:02d}_00_{eastwest}{lon:03d}_00_DEM/Copernicus_DSM_COG_10_{northsouth}{lat:02d}_00_{eastwest}{lon:03d}_00_DEM"
    )

    def tile(
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        reverse: bool = False,
        threads: int = MAX_THREADS,
        **kwargs: Any,
    ) -> ImageData:
        """Get Tile."""
        assets = self.assets_for_tile(tile_x, tile_y, tile_z)
        mosaic_assets = list(reversed(assets)) if reverse else assets

        def _reader(
            asset: str, tile_x: int, tile_y: int, tile_z: int, **kwargs: Any
        ) -> ImageData:
            with Reader(asset, tms=self.tms) as src:
                return src.tile(tile_x, tile_y, tile_z, **kwargs)

        return mosaic_reader(
            mosaic_assets,
            _reader,
            tile_x,
            tile_y,
            tile_z,
            threads=threads,
            allowed_exceptions=(TileOutsideBounds, RasterioIOError),
            **kwargs,
        )[0]

    def point(
        self,
        lon: float,
        lat: float,
        coord_crs: CRS = WGS84_CRS,
        reverse: bool = False,
        threads: int = MAX_THREADS,
        **kwargs: Any,
    ) -> PointData:
        """Get Point value."""
        assets = self.assets_for_point(lon, lat, coord_crs=coord_crs)
        mosaic_assets = list(reversed(assets)) if reverse else assets

        def _reader(asset: str, lon: float, lat: float, **kwargs) -> PointData:
            with Reader(asset, tms=self.tms) as src:
                return src.point(lon, lat, **kwargs)

        return mosaic_point_reader(
            mosaic_assets,
            _reader,
            lon,
            lat,
            threads=threads,
            allowed_exceptions=(PointOutsideBounds, RasterioIOError),
            **kwargs,
        )[0]

    def info(self) -> Info:
        """info."""
        meta = {
            "bounds": self.geographic_bounds,
            "minzoom": self.minzoom,
            "maxzoom": self.maxzoom,
            "band_metadata": [("b1", {})],
            "band_descriptions": [("b1", "")],
            "dtype": "float32",
            "colorinterp": ["grey"],
            "nodata_type": "None",
            "driver": "GTiff",
            "count": 1,
        }
        return Info(**meta)

    def statistics(self, **kwargs: Any) -> Dict[str, BandStatistics]:
        """Return Dataset's statistics."""
        # FOR NOW WE ONLY RETURN VALUE FROM THE FIRST FILE
        dataset = self.prefix_pattern.format(northsouth="N", eastwest="E", lat=0, lon=6)
        with Reader(f"{self._scheme}://{self.bucket}/{dataset}.tif") as src:
            return src.statistics(**kwargs)

    ############################################################################
    # Not Implemented methods
    # BaseReader required those method to be implemented
    def preview(self, *args, **kwargs):
        """Placeholder for BaseReader.preview."""
        raise NotImplementedError

    def part(self, *args, **kwargs):
        """Placeholder for BaseReader.part."""
        raise NotImplementedError

    def feature(self, *args, **kwargs):
        """Placeholder for BaseReader.feature."""
        raise NotImplementedError

    def assets_for_tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        xmin, ymin, xmax, ymax = self.tms.bounds(x, y, z)
        return self.assets_for_bbox(
            xmin, ymin, xmax, ymax, coord_crs=self.tms.rasterio_geographic_crs
        )

    def assets_for_bbox(
        self,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        coord_crs: Optional[CRS] = WGS84_CRS,
    ) -> List[str]:
        """Retrieve assets for bbox."""
        if coord_crs != WGS84_CRS:
            xmin, ymin, xmax, ymax = transform_bounds(
                coord_crs,
                WGS84_CRS,
                xmin,
                ymin,
                xmax,
                ymax,
            )

        xmin = int(xmin + 360)
        xmax = int(xmax + 360)
        ymax = int(ymax + 180)
        ymin = int(ymin + 180)

        files = []
        for x in range(xmin, xmax + 1, 1):
            for y in range(ymin, ymax + 1, 1):
                lon = x - 360
                lat = y - 180
                files.append(self._get_dataset_url(lon, lat))

        return files

    def assets_for_point(
        self,
        lon: float,
        lat: float,
        coord_crs: CRS = WGS84_CRS,
    ) -> List[str]:
        """Retrieve assets for point."""
        if coord_crs != WGS84_CRS:
            xs, ys = transform_coords(coord_crs, WGS84_CRS, [lon], [lat])
            lon, lat = xs[0], ys[0]

        return [self._get_dataset_url(lon, lat)]

    def _get_dataset_url(self, lon: float, lat: float) -> str:
        """Return dataset url."""
        northsouth = "N" if lat >= 0 else "S"
        eastwest = "W" if lon < 0 else "E"

        lat = abs(math.floor(lat))
        lon = abs(math.floor(lon))

        dataset = self.prefix_pattern.format(
            northsouth=northsouth, eastwest=eastwest, lat=lat, lon=lon
        )
        return f"{self._scheme}://{self.bucket}/{dataset}.tif"


@attr.s
class Dem90Reader(Dem30Reader):
    """Simple Mosaic reader for copernicus DEM"""

    input: str = attr.ib(default="copernicus-dem-90m")

    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    minzoom: int = attr.ib(default=6)
    maxzoom: int = attr.ib(default=7)

    bounds: BBox = attr.ib(init=False, default=(-180, -90, 180, 90))
    crs: CRS = attr.ib(init=False, default=WGS84_CRS)

    reader: Type[Reader] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(factory=dict)

    colormap: Dict = attr.ib(init=False, factory=dict)

    _scheme: str = "s3"
    bucket: str = attr.ib(default="copernicus-dem-90m")
    prefix_pattern: str = attr.ib(
        default="Copernicus_DSM_COG_30_{northsouth}{lat:02d}_00_{eastwest}{lon:03d}_00_DEM/Copernicus_DSM_COG_30_{northsouth}{lat:02d}_00_{eastwest}{lon:03d}_00_DEM"
    )

    def statistics(self, **kwargs: Any) -> Dict[str, BandStatistics]:
        """Return Dataset's statistics."""
        # FOR NOW WE ONLY RETURN VALUE FROM THE FIRST FILE
        dataset = self.prefix_pattern.format(
            northsouth="S", eastwest="W", lat=90, lon=164
        )
        with Reader(f"{self._scheme}://{self.bucket}/{dataset}.tif") as src:
            return src.statistics(**kwargs)
