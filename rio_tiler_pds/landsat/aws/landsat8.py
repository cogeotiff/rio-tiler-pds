"""AWS Landsat 8 reader."""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

import attr
import numpy
from rio_toa import toa_utils

from rio_tiler.errors import InvalidAssetName, MissingAssets
from rio_tiler.expression import apply_expression
from rio_tiler.io import BaseReader, COGReader
from rio_tiler.tasks import multi_arrays, multi_values
from rio_tiler.utils import pansharpening_brovey

from ...reader import MultiBandReader, get_object
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
        assets (tuple): list of available assets (default is ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'BQA')).
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
    assets: Tuple = attr.ib(init=False, default=landsat8_valid_bands)

    _scheme: str = "s3"
    _hostname: str = "landsat-pds"
    _prefix: str = "c1/L8/{path}/{row}/{scene}"

    def __enter__(self):
        """Support using with Context Managers."""
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
        return self

    def _get_asset_url(self, asset: str) -> str:
        """Validate band name and return asset's url."""
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")

        prefix = self._prefix.format(**self.scene_params)
        return f"{self._scheme}://{self._hostname}/{prefix}/{self.sceneid}_{asset}.TIF"

    def _convert_stats(self, statistics: Dict, asset: str):
        statistics["pc"] = dn_to_toa(
            numpy.array(statistics["pc"]), asset, self.mtl_metadata["L1_METADATA_FILE"]
        ).tolist()

        statistics["min"] = dn_to_toa(
            numpy.array([statistics["min"]]),
            asset,
            self.mtl_metadata["L1_METADATA_FILE"],
        )[0]

        statistics["max"] = dn_to_toa(
            numpy.array([statistics["max"]]),
            asset,
            self.mtl_metadata["L1_METADATA_FILE"],
        )[0]

        statistics["std"] = dn_to_toa(
            numpy.array([statistics["std"]]),
            asset,
            self.mtl_metadata["L1_METADATA_FILE"],
        )[0]

        statistics["histogram"][1] = dn_to_toa(
            numpy.array(statistics["histogram"][1]),
            asset,
            self.mtl_metadata["L1_METADATA_FILE"],
        ).tolist()
        return statistics

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
            nodata = 1 if asset == "BQA" else 0
            with self.reader(url, **self.reader_options) as cog:
                result = cog.stats(*args, nodata=nodata, **kwargs)[1]
                return self._convert_stats(result, asset)

        return multi_values(
            assets, _reader, pmin, pmax, hist_options=hist_options, **kwargs,
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
            nodata = 1 if asset == "BQA" else 0
            with self.reader(url, **self.reader_options) as cog:
                metadata = cog.metadata(*args, nodata=nodata, **kwargs)
                metadata["statistics"] = self._convert_stats(
                    metadata["statistics"][1], asset
                )
                return metadata

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

    def tile(
        self,
        tile_x: int,
        tile_y: int,
        tile_z: int,
        assets: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        asset_expression: Optional[
            str
        ] = "",  # Expression for each asset based on index names
        pan: bool = False,
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read a Mercator Map tile multiple assets."""
        if isinstance(assets, str):
            assets = (assets,)

        if expression:
            assets = self.parse_expression(expression)

        if not assets:
            raise MissingAssets(
                "bands must be passed either via expression or assets options."
            )

        if pan:
            assets = tuple(assets) + ("B8",)

        def _reader(
            asset: str, *args: Any, **kwargs: Any
        ) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_asset_url(asset)
            nodata = 1 if asset == "BQA" else 0
            with self.reader(url, **self.reader_options) as cog:
                tile, mask = cog.tile(*args, nodata=nodata, **kwargs)
                tile = dn_to_toa(tile, asset, self.mtl_metadata["L1_METADATA_FILE"])
            return tile, mask

        data, mask = multi_arrays(
            assets,
            _reader,
            tile_x,
            tile_y,
            tile_z,
            expression=asset_expression,
            **kwargs,
        )

        if pan:
            assets = assets[:-1]
            data = pansharpening_brovey(data[:-1], data[-1], 0.2, data.dtype)

        if expression:
            blocks = expression.split(",")
            data = apply_expression(blocks, assets, data)

        return data, mask

    def part(
        self,
        bbox: Tuple[float, float, float, float],
        max_size: int = 1024,
        assets: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        asset_expression: Optional[
            str
        ] = "",  # Expression for each asset based on index names
        pan: bool = False,
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Read part of multiple assets."""
        if isinstance(assets, str):
            assets = (assets,)

        if expression:
            assets = self.parse_expression(expression)

        if not assets:
            raise MissingAssets(
                "bands must be passed either via expression or assets options."
            )

        if pan:
            assets = tuple(assets) + ("B8",)

        def _reader(
            asset: str, *args: Any, **kwargs: Any
        ) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_asset_url(asset)
            nodata = 1 if asset == "BQA" else 0
            with self.reader(url, **self.reader_options) as cog:
                data, mask = cog.part(*args, nodata=nodata, **kwargs)
                data = dn_to_toa(data, asset, self.mtl_metadata["L1_METADATA_FILE"])
            return data, mask

        data, mask = multi_arrays(
            assets, _reader, bbox, expression=asset_expression, **kwargs,
        )

        if pan:
            assets = assets[:-1]
            data = pansharpening_brovey(data[:-1], data[-1], 0.2, data.dtype)

        if expression:
            blocks = expression.split(",")
            data = apply_expression(blocks, assets, data)

        return data, mask

    def preview(
        self,
        assets: Union[Sequence[str], str] = None,
        expression: Optional[str] = "",
        asset_expression: Optional[
            str
        ] = "",  # Expression for each asset based on index names
        pan: bool = False,
        **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Return a preview from multiple assets."""
        if isinstance(assets, str):
            assets = (assets,)

        if expression:
            assets = self.parse_expression(expression)

        if not assets:
            raise MissingAssets(
                "bands must be passed either via expression or assets options."
            )

        if pan:
            assets = tuple(assets) + ("B8",)

        def _reader(asset: str, **kwargs: Any) -> Tuple[numpy.ndarray, numpy.ndarray]:
            url = self._get_asset_url(asset)
            nodata = 1 if asset == "BQA" else 0
            with self.reader(url, **self.reader_options) as cog:
                data, mask = cog.preview(nodata=nodata, **kwargs)
                data = dn_to_toa(data, asset, self.mtl_metadata["L1_METADATA_FILE"])
            return data, mask

        data, mask = multi_arrays(
            assets, _reader, expression=asset_expression, **kwargs
        )

        if pan:
            assets = assets[:-1]
            data = pansharpening_brovey(data[:-1], data[-1], 0.2, data.dtype)

        if expression:
            blocks = expression.split(",")
            data = apply_expression(blocks, assets, data)

        return data, mask

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
        """Read a value from COGs."""
        if isinstance(assets, str):
            assets = (assets,)

        if expression:
            assets = self.parse_expression(expression)

        if not assets:
            raise MissingAssets(
                "bands must be passed either via expression or assets options."
            )

        def _reader(asset: str, *args, **kwargs: Any) -> Dict:
            url = self._get_asset_url(asset)
            nodata = 1 if asset == "BQA" else 0
            with self.reader(url, **self.reader_options) as cog:
                data = numpy.array(cog.point(*args, nodata=nodata, **kwargs))
                data = dn_to_toa(data, asset, self.mtl_metadata["L1_METADATA_FILE"])
            return data.tolist()[0]

        data = multi_values(
            assets, _reader, lon, lat, expression=asset_expression, **kwargs,
        )

        values = [d for _, d in data.items()]
        if expression:
            blocks = expression.split(",")
            values = apply_expression(blocks, assets, values).tolist()

        return values
