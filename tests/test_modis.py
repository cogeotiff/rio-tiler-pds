"""tests rio_tiler.sentinel2"""

import os
from unittest.mock import patch

import pytest
import rasterio

from rio_tiler.errors import InvalidBandName
from rio_tiler_pds.errors import InvalidMODISProduct, InvalidMODISSceneId
from rio_tiler_pds.modis.aws import MODISPDSReader
from rio_tiler_pds.modis.modland_grid import InvalidModlandGridID, tile_bbox
from rio_tiler_pds.modis.utils import sceneid_parser

MODIS_PDS_BUCKET = os.path.join(os.path.dirname(__file__), "fixtures", "modis-pds")
MCD43A4_SCENE = "MCD43A4.A2017006.h21v11.006.2017018074804"
MOD09GA_SCENE = "MOD09GA.A2017129.h34v07.006.2017137214839"
MOD09GQ_SCENE = "MOD09GQ.A2017120.h29v09.006.2017122031126"
MYD09GA_SCENE = "MYD09GA.A2017114.h27v11.006.2017116032728"
MYD09GQ_SCENE = "MYD09GQ.A2017114.h28v07.006.2017116033344"


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
    assert band.startswith("s3://modis-pds")
    band = band.replace("s3://modis-pds", MODIS_PDS_BUCKET)
    return rasterio.open(band)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWS_MODISPDSReader(rio):
    """Test MODIS Reader."""
    rio.open = mock_rasterio_open

    with pytest.raises(InvalidMODISSceneId):
        with MODISPDSReader("D43A4.A2017006.h21v11.006.2017018074804"):
            pass

    with pytest.raises(InvalidMODISProduct):
        with MODISPDSReader("MOD00A4.A2017006.h21v11.006.2017018074804"):
            pass

    with MODISPDSReader(MCD43A4_SCENE) as modis:
        assert modis.scene_params.get("scene") == MCD43A4_SCENE
        assert len(modis.bounds) == 4
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

        with pytest.raises(InvalidBandName):
            modis._get_band_url("granule")

        assert modis._get_band_url("B1") == modis._get_band_url("B01")

        assert modis._get_band_url("B01") == (
            "s3://modis-pds/MCD43A4.006/21/11/2017006/MCD43A4.A2017006.h21v11.006.2017018074804_B01.TIF"
        )

        metadata = modis.info(bands="B01")
        assert metadata["band_descriptions"] == [("B01", "Nadir_Reflectance_Band1")]

        with pytest.warns(UserWarning):
            stats = modis.statistics()
        assert list(stats) == list(modis.bands)

        stats = modis.statistics(bands="B05")
        assert len(stats.items()) == 1
        assert stats["B05"]["percentile_2"]
        assert stats["B05"]["percentile_98"]

        tile_z = 7
        tile_x = 76
        tile_y = 73
        data, mask = modis.tile(tile_x, tile_y, tile_z, bands="B01")
        assert data.shape == (1, 256, 256)
        assert mask.shape == (256, 256)

    with MODISPDSReader(MOD09GA_SCENE) as modis:
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
        assert modis._get_band_url("B01") == (
            "s3://modis-pds/MOD09GA.006/34/07/2017129/MOD09GA.A2017129.h34v07.006.2017137214839_B01.TIF"
        )

    with MODISPDSReader(MOD09GQ_SCENE) as modis:
        assert modis.minzoom == 4
        assert modis.maxzoom == 9
        assert modis.bands == (
            "B01",
            "B02",
            "granule",
            "numobs",
            "obscov",
            "obsnum",
            "orbit",
            "qc",
        )
        assert modis._get_band_url("B01") == (
            "s3://modis-pds/MOD09GQ.006/29/09/2017120/MOD09GQ.A2017120.h29v09.006.2017122031126_B01.TIF"
        )

    with MODISPDSReader(MYD09GA_SCENE) as modis:
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
        assert modis._get_band_url("B01") == (
            "s3://modis-pds/MYD09GA.006/27/11/2017114/MYD09GA.A2017114.h27v11.006.2017116032728_B01.TIF"
        )

    with MODISPDSReader(MYD09GQ_SCENE) as modis:
        assert modis.minzoom == 4
        assert modis.maxzoom == 9
        assert modis.bands == (
            "B01",
            "B02",
            "granule",
            "numobs",
            "obscov",
            "obsnum",
            "orbit",
            "qc",
        )
        assert modis._get_band_url("B01") == (
            "s3://modis-pds/MYD09GQ.006/28/07/2017114/MYD09GQ.A2017114.h28v07.006.2017116033344_B01.TIF"
        )


def test_modland_lookup():
    """Parse valid MOSAIC sceneids and return metadata."""
    with pytest.raises(InvalidModlandGridID):
        tile_bbox("00", "00")
    assert tile_bbox("14", "00") == (-180.0, 80.0, -172.7151, 80.4083)


def test_modis_id():
    """Parse valid MODIS sceneids and return metadata."""
    with pytest.raises(InvalidMODISSceneId):
        sceneid_parser("D43A4.A2017006.h21v11.006.2017018074804")

    expected_content = {
        "product": "MCD43A4",
        "date": "2017006",
        "horizontal_grid": "21",
        "vertical_grid": "11",
        "version": "006",
        "acquisitionYear": "2017",
        "acquisitionDOY": "018",
        "scene": "MCD43A4.A2017006.h21v11.006.2017018074804",
    }
    assert sceneid_parser(MCD43A4_SCENE) == expected_content

    expected_content = {
        "product": "MOD09GA",
        "date": "2017129",
        "horizontal_grid": "34",
        "vertical_grid": "07",
        "version": "006",
        "acquisitionYear": "2017",
        "acquisitionDOY": "137",
        "scene": "MOD09GA.A2017129.h34v07.006.2017137214839",
    }
    assert sceneid_parser(MOD09GA_SCENE) == expected_content

    expected_content = {
        "product": "MOD09GQ",
        "date": "2017120",
        "horizontal_grid": "29",
        "vertical_grid": "09",
        "version": "006",
        "acquisitionYear": "2017",
        "acquisitionDOY": "122",
        "scene": "MOD09GQ.A2017120.h29v09.006.2017122031126",
    }
    assert sceneid_parser(MOD09GQ_SCENE) == expected_content

    expected_content = {
        "product": "MYD09GA",
        "date": "2017114",
        "horizontal_grid": "27",
        "vertical_grid": "11",
        "version": "006",
        "acquisitionYear": "2017",
        "acquisitionDOY": "116",
        "scene": "MYD09GA.A2017114.h27v11.006.2017116032728",
    }
    assert sceneid_parser(MYD09GA_SCENE) == expected_content

    expected_content = {
        "product": "MYD09GQ",
        "date": "2017114",
        "horizontal_grid": "28",
        "vertical_grid": "07",
        "version": "006",
        "acquisitionYear": "2017",
        "acquisitionDOY": "116",
        "scene": "MYD09GQ.A2017114.h28v07.006.2017116033344",
    }
    assert sceneid_parser(MYD09GQ_SCENE) == expected_content
