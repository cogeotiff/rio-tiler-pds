"""tests rio_tiler.sentinel2"""

import os
from unittest.mock import patch

import pytest
import rasterio

from rio_tiler.errors import InvalidBandName, TileOutsideBounds
from rio_tiler_pds.cbers.aws import CBERSReader
from rio_tiler_pds.cbers.utils import sceneid_parser
from rio_tiler_pds.errors import InvalidCBERSSceneId

CBERS_BUCKET = os.path.join(os.path.dirname(__file__), "fixtures", "cbers-pds")
# CBERS4 test scenes
CBERS_MUX_SCENE = "CBERS_4_MUX_20171121_057_094_L2"
CBERS_AWFI_SCENE = "CBERS_4_AWFI_20170420_146_129_L2"
CBERS_PAN10M_SCENE = "CBERS_4_PAN10M_20170427_161_109_L4"
CBERS_PAN5M_SCENE = "CBERS_4_PAN5M_20170425_153_114_L4"
# CBERS4A test scenes
CBERS_4A_MUX_SCENE = "CBERS_4A_MUX_20200808_201_137_L4"
CBERS_4A_WPM_SCENE = "CBERS_4A_WPM_20200730_209_139_L4"
CBERS_4A_WFI_SCENE = "CBERS_4A_WFI_20200801_221_156_L4"


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
    assert band.startswith("s3://cbers-pds")
    band = band.replace("s3://cbers-pds", CBERS_BUCKET)
    return rasterio.open(band)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_CB4_MUX(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    scene = "CBERS_4_MUX_20171121_057_094"
    with pytest.raises(InvalidCBERSSceneId):
        with CBERSReader(scene):
            pass

    with CBERSReader(CBERS_MUX_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_MUX_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.bands == ("B5", "B6", "B7", "B8")

        with pytest.warns(UserWarning):
            meta = cbers.info()
        assert meta.band_descriptions == [
            ("B5", ""),
            ("B6", ""),
            ("B7", ""),
            ("B8", ""),
        ]

        with pytest.raises(InvalidBandName):
            cbers.info(bands="BAND5")

        metadata = cbers.info(bands="B5")
        assert len(metadata["band_metadata"]) == 1
        assert metadata["band_descriptions"] == [("B5", "")]

        metadata = cbers.info(bands=cbers.bands)
        assert len(metadata["band_metadata"]) == 4
        assert metadata["band_descriptions"] == [
            ("B5", ""),
            ("B6", ""),
            ("B7", ""),
            ("B8", ""),
        ]

        with pytest.warns(UserWarning):
            stats = cbers.statistics()
        assert list(stats) == ["B5", "B6", "B7", "B8"]

        stats = cbers.statistics(bands="B5")
        assert len(stats.items()) == 1
        assert stats["B5"]["percentile_2"]
        assert stats["B5"]["percentile_98"]

        stats = cbers.statistics(bands=cbers.bands, hist_options={"bins": 20})
        assert len(stats["B5"]["histogram"][0]) == 20

        tile_z = 10
        tile_x = 664
        tile_y = 495
        data, mask = cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)

        tile_z = 10
        tile_x = 694
        tile_y = 495
        with pytest.raises(TileOutsideBounds):
            cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])

        tile_z = 10
        tile_x = 664
        tile_y = 495
        data, mask = cbers.tile(
            tile_x, tile_y, tile_z, expression="B8*0.8, B7*1.1, B6*0.8"
        )
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_CB4_AWFI(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_AWFI_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_AWFI_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.bands == ("B13", "B14", "B15", "B16")

        tile_z = 10
        tile_x = 401
        tile_y = 585
        data, mask = cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_CB4_PAN10M(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_PAN10M_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_PAN10M_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.bands == ("B2", "B3", "B4")

        tile_z = 10
        tile_x = 370
        tile_y = 535
        data, mask = cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_CB4_PAN5M(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_PAN5M_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_PAN5M_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.bands == ("B1",)

        tile_z = 10
        tile_x = 390
        tile_y = 547
        data, mask = cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_CB4A_MUX(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_4A_MUX_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_4A_MUX_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.bands == ("B5", "B6", "B7", "B8")

        with pytest.warns(UserWarning):
            meta = cbers.info()
        assert meta.band_descriptions == [
            ("B5", ""),
            ("B6", ""),
            ("B7", ""),
            ("B8", ""),
        ]

        with pytest.raises(InvalidBandName):
            cbers.info(bands="BAND5")

        metadata = cbers.info(bands="B5")
        assert len(metadata["band_metadata"]) == 1
        assert metadata["band_descriptions"] == [("B5", "")]

        metadata = cbers.info(bands=cbers.bands)
        assert len(metadata["band_metadata"]) == 4
        assert metadata["band_descriptions"] == [
            ("B5", ""),
            ("B6", ""),
            ("B7", ""),
            ("B8", ""),
        ]

        with pytest.warns(UserWarning):
            stats = cbers.statistics()
        assert list(stats) == ["B5", "B6", "B7", "B8"]

        stats = cbers.statistics(bands="B5")
        assert len(stats.items()) == 1
        assert stats["B5"]["percentile_2"]
        assert stats["B5"]["percentile_98"]

        stats = cbers.statistics(bands=cbers.bands, hist_options={"bins": 20})
        assert len(stats["B5"]["histogram"][0]) == 20

        tile_z = 10
        tile_x = 385
        tile_y = 567
        data, mask = cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)

        tile_z = 10
        tile_x = 694
        tile_y = 495
        with pytest.raises(TileOutsideBounds):
            cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])

        tile_z = 10
        tile_x = 385
        tile_y = 567
        data, mask = cbers.tile(
            tile_x, tile_y, tile_z, expression="B8*0.8, B7*1.1, B6*0.8"
        )
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_CB4A_WPM(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_4A_WPM_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_4A_WPM_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.bands == ("B0", "B1", "B2", "B3", "B4")

        tile_z = 10
        tile_x = 366
        tile_y = 572
        data, mask = cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_CB4A_WFI(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_4A_WFI_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_4A_WFI_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.bands == ("B13", "B14", "B15", "B16")

        tile_z = 10
        tile_x = 316
        tile_y = 614
        data, mask = cbers.tile(tile_x, tile_y, tile_z, bands=cbers.scene_params["rgb"])
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


def test_cbers_id_valid():
    """Parse valid CBERS sceneids and return metadata."""
    scene = "CBERS_4_MUX_20171121_057_094_L2"
    expected_content = {
        "satellite": "CBERS",
        "mission": "4",
        "instrument": "MUX",
        "acquisitionYear": "2017",
        "acquisitionMonth": "11",
        "acquisitionDay": "21",
        "path": "057",
        "row": "094",
        "processingCorrectionLevel": "L2",
        "scene": "CBERS_4_MUX_20171121_057_094_L2",
        "date": "2017-11-21",
        "reference_band": "B6",
        "bands": ("B5", "B6", "B7", "B8"),
        "rgb": ("B7", "B6", "B5"),
    }

    assert sceneid_parser(scene) == expected_content

    scene = "CBERS_4_AWFI_20171121_057_094_L2"
    expected_content = {
        "satellite": "CBERS",
        "mission": "4",
        "instrument": "AWFI",
        "acquisitionYear": "2017",
        "acquisitionMonth": "11",
        "acquisitionDay": "21",
        "path": "057",
        "row": "094",
        "processingCorrectionLevel": "L2",
        "scene": "CBERS_4_AWFI_20171121_057_094_L2",
        "date": "2017-11-21",
        "reference_band": "B14",
        "bands": ("B13", "B14", "B15", "B16"),
        "rgb": ("B15", "B14", "B13"),
    }

    assert sceneid_parser(scene) == expected_content

    scene = "CBERS_4_PAN10M_20171121_057_094_L2"
    expected_content = {
        "satellite": "CBERS",
        "mission": "4",
        "instrument": "PAN10M",
        "acquisitionYear": "2017",
        "acquisitionMonth": "11",
        "acquisitionDay": "21",
        "path": "057",
        "row": "094",
        "processingCorrectionLevel": "L2",
        "scene": "CBERS_4_PAN10M_20171121_057_094_L2",
        "date": "2017-11-21",
        "reference_band": "B4",
        "bands": ("B2", "B3", "B4"),
        "rgb": ("B3", "B4", "B2"),
    }

    assert sceneid_parser(scene) == expected_content

    scene = "CBERS_4_PAN5M_20171121_057_094_L2"
    expected_content = {
        "satellite": "CBERS",
        "mission": "4",
        "instrument": "PAN5M",
        "acquisitionYear": "2017",
        "acquisitionMonth": "11",
        "acquisitionDay": "21",
        "path": "057",
        "row": "094",
        "processingCorrectionLevel": "L2",
        "scene": "CBERS_4_PAN5M_20171121_057_094_L2",
        "date": "2017-11-21",
        "reference_band": "B1",
        "bands": ("B1",),
        "rgb": ("B1", "B1", "B1"),
    }

    scene = "CBERS_4A_MUX_20200808_201_137_L4"
    expected_content = {
        "satellite": "CBERS",
        "mission": "4A",
        "instrument": "MUX",
        "acquisitionYear": "2020",
        "acquisitionMonth": "08",
        "acquisitionDay": "08",
        "path": "201",
        "row": "137",
        "processingCorrectionLevel": "L4",
        "scene": "CBERS_4A_MUX_20200808_201_137_L4",
        "date": "2020-08-08",
        "reference_band": "B6",
        "bands": ("B5", "B6", "B7", "B8"),
        "rgb": ("B7", "B6", "B5"),
    }

    # Same as above testing 2A and 2B levels
    scene = "CBERS_4A_MUX_20200808_201_137_L2A"
    expected_content = {
        "satellite": "CBERS",
        "mission": "4A",
        "instrument": "MUX",
        "acquisitionYear": "2020",
        "acquisitionMonth": "08",
        "acquisitionDay": "08",
        "path": "201",
        "row": "137",
        "processingCorrectionLevel": "L2A",
        "scene": "CBERS_4A_MUX_20200808_201_137_L2A",
        "date": "2020-08-08",
        "reference_band": "B6",
        "bands": ("B5", "B6", "B7", "B8"),
        "rgb": ("B7", "B6", "B5"),
    }

    assert sceneid_parser(scene) == expected_content

    scene = "CBERS_4A_WFI_20200801_221_156_L4"
    expected_content = {
        "satellite": "CBERS",
        "mission": "4A",
        "instrument": "WFI",
        "acquisitionYear": "2020",
        "acquisitionMonth": "08",
        "acquisitionDay": "01",
        "path": "221",
        "row": "156",
        "processingCorrectionLevel": "L4",
        "scene": "CBERS_4A_WFI_20200801_221_156_L4",
        "date": "2020-08-01",
        "reference_band": "B14",
        "bands": ("B13", "B14", "B15", "B16"),
        "rgb": ("B15", "B14", "B13"),
    }

    assert sceneid_parser(scene) == expected_content

    scene = "CBERS_4A_WPM_20200730_209_139_L4"
    expected_content = {
        "satellite": "CBERS",
        "mission": "4A",
        "instrument": "WPM",
        "acquisitionYear": "2020",
        "acquisitionMonth": "07",
        "acquisitionDay": "30",
        "path": "209",
        "row": "139",
        "processingCorrectionLevel": "L4",
        "scene": "CBERS_4A_WPM_20200730_209_139_L4",
        "date": "2020-07-30",
        "reference_band": "B2",
        "bands": ("B0", "B1", "B2", "B3", "B4"),
        "rgb": ("B3", "B2", "B1"),
    }

    assert sceneid_parser(scene) == expected_content
