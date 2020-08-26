"""tests rio_tiler.sentinel2"""

import os
from unittest.mock import patch

import pytest
import rasterio

from rio_tiler.errors import InvalidAssetName, MissingAssets, TileOutsideBounds
from rio_tiler_pds.cbers.aws import CBERSReader
from rio_tiler_pds.cbers.utils import sceneid_parser
from rio_tiler_pds.errors import InvalidCBERSSceneId

CBERS_BUCKET = os.path.join(os.path.dirname(__file__), "fixtures", "cbers-pds")
CBERS_MUX_SCENE = "CBERS_4_MUX_20171121_057_094_L2"
CBERS_AWFI_SCENE = "CBERS_4_AWFI_20170420_146_129_L2"
CBERS_PAN10M_SCENE = "CBERS_4_PAN10M_20170427_161_109_L4"
CBERS_PAN5M_SCENE = "CBERS_4_PAN5M_20170425_153_114_L4"
# Currently not being used, not defining for new instruments
CBERS_MUX_PATH = os.path.join(
    CBERS_BUCKET, "CBERS4/MUX/057/094/CBERS_4_MUX_20171121_057_094_L2/"
)


@pytest.fixture(autouse=True)
def testing_env_var(monkeypatch):
    """Set fake env to make sure we don't hit AWS services."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "jqt")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "rde")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", "/tmp/noconfigheere")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "/tmp/noconfighereeither")
    monkeypatch.setenv("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")


def mock_rasterio_open(asset):
    """Mock rasterio Open."""
    assert asset.startswith("s3://cbers-pds")
    asset = asset.replace("s3://cbers-pds", CBERS_BUCKET)
    return rasterio.open(asset)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_MUX(rio):
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
        assert cbers.assets == ("B5", "B6", "B7", "B8")

        with pytest.raises(MissingAssets):
            cbers.info()

        with pytest.raises(InvalidAssetName):
            cbers.info(assets="BAND5")

        metadata = cbers.info(assets="B5")
        assert len(metadata["band_metadata"]) == 1
        assert metadata["band_descriptions"] == [(1, "B5")]

        metadata = cbers.info(assets=cbers.assets)
        assert len(metadata["band_metadata"]) == 4
        assert metadata["band_descriptions"] == [
            (1, "B5"),
            (2, "B6"),
            (3, "B7"),
            (4, "B8"),
        ]

        with pytest.raises(MissingAssets):
            cbers.stats()

        stats = cbers.stats(assets="B5")
        assert len(stats.items()) == 1
        assert stats["B5"]["pc"] == [28, 98]

        stats = cbers.stats(assets=cbers.assets, hist_options=dict(bins=20))
        assert len(stats["B5"]["histogram"][0]) == 20

        with pytest.raises(MissingAssets):
            cbers.metadata()

        metadata = cbers.metadata(assets="B5")
        assert metadata["statistics"]["B5"]["pc"] == [28, 98]

        metadata = cbers.metadata(assets=cbers.assets)
        assert metadata["statistics"]["B5"]["pc"] == [28, 98]
        assert len(metadata["band_metadata"]) == 4
        assert metadata["band_descriptions"] == [
            (1, "B5"),
            (2, "B6"),
            (3, "B7"),
            (4, "B8"),
        ]

        tile_z = 10
        tile_x = 664
        tile_y = 495
        data, mask = cbers.tile(
            tile_x, tile_y, tile_z, assets=cbers.scene_params["rgb"]
        )
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)

        tile_z = 10
        tile_x = 694
        tile_y = 495
        with pytest.raises(TileOutsideBounds):
            cbers.tile(tile_x, tile_y, tile_z, assets=cbers.scene_params["rgb"])

        tile_z = 10
        tile_x = 664
        tile_y = 495
        data, mask = cbers.tile(
            tile_x, tile_y, tile_z, expression="B8*0.8, B7*1.1, B6*0.8"
        )
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_AWFI(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_AWFI_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_AWFI_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.assets == ("B13", "B14", "B15", "B16")

        tile_z = 10
        tile_x = 401
        tile_y = 585
        data, mask = cbers.tile(
            tile_x, tile_y, tile_z, assets=cbers.scene_params["rgb"]
        )
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_PAN10M(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_PAN10M_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_PAN10M_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.assets == ("B2", "B3", "B4")

        tile_z = 10
        tile_x = 370
        tile_y = 535
        data, mask = cbers.tile(
            tile_x, tile_y, tile_z, assets=cbers.scene_params["rgb"]
        )
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_CBERSReader_PAN5M(rio):
    """Should work as expected (get bounds)"""
    rio.open = mock_rasterio_open

    with CBERSReader(CBERS_PAN5M_SCENE) as cbers:
        bounds = cbers.bounds
        assert cbers.scene_params.get("scene") == CBERS_PAN5M_SCENE
        assert len(bounds) == 4
        assert cbers.minzoom
        assert cbers.maxzoom
        assert cbers.assets == ("B1",)

        tile_z = 10
        tile_x = 390
        tile_y = 547
        data, mask = cbers.tile(
            tile_x, tile_y, tile_z, assets=cbers.scene_params["rgb"]
        )
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

    assert sceneid_parser(scene) == expected_content
