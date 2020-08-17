"""MultiBand reader."""

from typing import Any, Dict, Optional, Sequence, Tuple, Union

import attr

from rio_tiler.errors import MissingAssets
from rio_tiler.io import MultiBaseReader
from rio_tiler.tasks import multi_values


@attr.s
class MultiBandReader(MultiBaseReader):
    """AWS Public Dataset CBERS 4 reader."""

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
        """Return Dataset's spatial info."""
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
