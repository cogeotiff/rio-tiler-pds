"""tests rio_tiler.sentinel2"""

import os
from unittest.mock import patch

import pytest
import rasterio

from rio_tiler.errors import InvalidBandName
from rio_tiler_pds.errors import InvalidMODISProduct
from rio_tiler_pds.modis.aws import MODISASTRAEAReader

MODIS_AST_BUCKET = os.path.join(
    os.path.dirname(__file__), "fixtures", "astraea-opendata"
)
MCD43A4_SCENE = "MCD43A4.A2017200.h21v11.006.2017209030811"
MOD11A1_SCENE = "MOD11A1.A2020250.h20v11.006.2020251085003"
MYD11A1_SCENE = "MYD11A1.A2008110.h16v12.006.2015345131628"
MOD13A1_SCENE = "MOD13A1.A2020049.h14v04.006.2020066002045"
MYD13A1_SCENE = "MYD13A1.A2020153.h30v10.006.2020170024036"


@pytest.fixture(autouse=True)
def testing_env_var(monkeypatch):
    """Set fake env to make sure we don't hit AWS services."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "jqt")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "rde")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", "/tmp/noconfigheere")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "/tmp/noconfighereeither")
    monkeypatch.setenv("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")


def mock_rasterio_open(band):
    """Mock rasterio Open."""
    assert band.startswith("s3://astraea-opendata")
    band = band.replace("s3://astraea-opendata", MODIS_AST_BUCKET)
    return rasterio.open(band)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWS_MODISASTRAEAReader(rio):
    """Test MODIS (ASTRAEA) Reader product."""
    rio.open = mock_rasterio_open

    with pytest.raises(InvalidMODISProduct):
        with MODISASTRAEAReader("MOD00A4.A2017006.h21v11.006.2017018074804"):
            pass

    with MODISASTRAEAReader(MCD43A4_SCENE) as modis:
        assert modis.minzoom == 4
        assert modis.maxzoom == 9
        assert modis.bands == (
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

        assert modis._get_band_url("B1") == modis._get_band_url("B01")

        assert modis._get_band_url("B01") == (
            "s3://astraea-opendata/MCD43A4.006/21/11/2017200/MCD43A4.A2017200.h21v11.006.2017209030811_B01.TIF"
        )

    with MODISASTRAEAReader(MOD11A1_SCENE) as modis:
        assert modis.minzoom == 4
        assert modis.maxzoom == 9
        assert modis.bands == (
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B09",
            "B10",
            "B11",
            "B12",
        )

        assert modis._get_band_url("B01") == (
            "s3://astraea-opendata/MOD11A1.006/20/11/2020250/MOD11A1.A2020250.h20v11.006.2020251085003_LSTD_B01.TIF"
        )

    with MODISASTRAEAReader(MYD11A1_SCENE) as modis:
        assert modis.minzoom == 4
        assert modis.maxzoom == 9
        assert modis.bands == (
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B09",
            "B10",
            "B11",
            "B12",
        )

        assert modis._get_band_url("B01") == (
            "s3://astraea-opendata/MYD11A1.006/16/12/2008110/MYD11A1.A2008110.h16v12.006.2015345131628_LSTD_B01.TIF"
        )

    with MODISASTRAEAReader(MOD13A1_SCENE) as modis:
        assert modis.minzoom == 4
        assert modis.maxzoom == 9
        assert modis.bands == (
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B09",
            "B10",
            "B11",
            "B12",
        )

        assert modis._get_band_url("B01") == (
            "s3://astraea-opendata/MOD13A1.006/14/04/2020049/MOD13A1.A2020049.h14v04.006.2020066002045_NDVI_B01.TIF"
        )

    with MODISASTRAEAReader(MYD13A1_SCENE) as modis:
        assert modis.scene_params.get("scene") == MYD13A1_SCENE
        assert len(modis.bounds) == 4
        assert modis.minzoom == 4
        assert modis.maxzoom == 9
        assert modis.bands == (
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B09",
            "B10",
            "B11",
            "B12",
        )

        with pytest.raises(InvalidBandName):
            modis._get_band_url("granule")

        assert modis._get_band_url("B01") == (
            "s3://astraea-opendata/MYD13A1.006/30/10/2020153/MYD13A1.A2020153.h30v10.006.2020170024036_NDVI_B01.TIF"
        )

        metadata = modis.info(bands="B01")
        assert metadata["band_descriptions"] == [(1, "B01")]

        metadata = modis.metadata(bands=("B01", "B02"))
        assert metadata["band_descriptions"] == [(1, "B01"), (2, "B02")]

        stats = modis.stats(bands="B05")
        assert len(stats.items()) == 1
        assert stats["B05"]["pc"]

        tile_z = 8
        tile_x = 219
        tile_y = 141
        data, mask = modis.tile(tile_x, tile_y, tile_z, bands="B01")
        assert data.shape == (1, 256, 256)
        assert mask.shape == (256, 256)
