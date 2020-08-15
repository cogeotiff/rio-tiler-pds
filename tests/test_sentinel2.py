"""tests rio_tiler.sentinel2"""

import os
from unittest.mock import patch

import pytest
import rasterio

from rio_tiler.errors import InvalidAssetName
from rio_tiler_pds.errors import InvalidSentinelSceneId
from rio_tiler_pds.sentinel import AWSPDS_S2L1CReader, AWSPDS_S2L2AReader
from rio_tiler_pds.sentinel.utils import s2_sceneid_parser

SENTINEL_SCENE_L1 = "S2A_L1C_20170729_19UDP_0"
SENTINEL_SCENE_L2 = "S2A_L2A_20170729_19UDP_0"
SENTINEL_BUCKET = os.path.join(os.path.dirname(__file__), "fixtures", "sentinel-s2")

L1C_TJSON_PATH = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "sentinel-s2-l1c",
    "tiles",
    "19",
    "U",
    "DP",
    "2017",
    "7",
    "29",
    "0",
    "tileInfo.json",
)
with open(L1C_TJSON_PATH, "rb") as f:
    L1C_TILEJSON = f.read()


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
    """Mock rasterio Open for Sentinel2 dataset."""
    assert asset.startswith("s3://sentinel-s2-l")
    asset = asset.replace("s3://sentinel-s2", SENTINEL_BUCKET)
    return rasterio.open(asset)


@patch("rio_tiler_pds.sentinel.awspds_sentinel2.aws_get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_S2L1CReader(rio, get_object):
    """Test AWSPDS_S2L1CReader."""
    rio.open = mock_rasterio_open
    get_object.return_value = L1C_TILEJSON

    with pytest.raises(InvalidSentinelSceneId):
        with AWSPDS_S2L1CReader("S2A_tile_20170323_17SNC"):
            pass

    with AWSPDS_S2L1CReader(SENTINEL_SCENE_L1) as sentinel:
        assert sentinel.scene_params["scene"] == SENTINEL_SCENE_L1
        assert sentinel.minzoom == 8
        assert sentinel.maxzoom == 14
        assert len(sentinel.bounds) == 4
        assert sentinel.assets == (
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B09",
            "B11",
            "B12",
            "B8A",
        )
        with pytest.raises(InvalidAssetName):
            sentinel.stats(assets="B1")

        stats = sentinel.stats(assets="B01")
        assert stats["B01"]["pc"] == [1094, 8170]

        metadata = sentinel.metadata(assets="B01")
        assert metadata["statistics"]["B01"]["pc"] == [1094, 8170]

        tile_z = 8
        tile_x = 78
        tile_y = 89
        data, mask = sentinel.tile(tile_x, tile_y, tile_z, assets=("B04", "B03", "B02"))
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)


L2A_TJSON_PATH = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "sentinel-s2-l2a",
    "tiles",
    "19",
    "U",
    "DP",
    "2017",
    "7",
    "29",
    "0",
    "tileInfo.json",
)
with open(L2A_TJSON_PATH, "rb") as f:
    L2A_TILEJSON = f.read()


@patch("rio_tiler_pds.sentinel.awspds_sentinel2.aws_get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_S2L2AReader(rio, get_object):
    """Test AWSPDS_S2L2AReader."""
    rio.open = mock_rasterio_open
    get_object.return_value = L2A_TILEJSON

    with pytest.raises(InvalidSentinelSceneId):
        with AWSPDS_S2L1CReader("S2A_tile_20170323_17SNC"):
            pass

    with AWSPDS_S2L2AReader(SENTINEL_SCENE_L2) as sentinel:
        assert sentinel.scene_params["scene"] == SENTINEL_SCENE_L2
        assert sentinel.minzoom == 8
        assert sentinel.maxzoom == 14
        assert len(sentinel.bounds) == 4
        assert sentinel.assets == (
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B09",
            "B11",
            "B12",
            "B8A",
            "AOT",
            "SCL",
            "WVP",
        )
        with pytest.raises(InvalidAssetName):
            sentinel.stats(assets="B1")

        stats = sentinel.stats(assets="B01")
        assert stats["B01"]["pc"] == [1094, 8170]

        metadata = sentinel.metadata(assets="B01")
        assert metadata["statistics"]["B01"]["pc"] == [1094, 8170]

        tile_z = 8
        tile_x = 78
        tile_y = 89
        data, mask = sentinel.tile(tile_x, tile_y, tile_z, assets=("B04", "B03", "B02"))
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)

        assert sentinel._get_resolution("B01") == "60"
        assert sentinel._get_resolution("B02") == "10"
        assert sentinel._get_resolution("B06") == "20"
        assert sentinel._get_resolution("AOT") == "10"
        assert sentinel._get_resolution("SCL") == "20"


def test_sentinel_newid_valid():
    """Parse sentinel-2 valid sceneid and return metadata."""
    expected_content = {
        "sensor": "2",
        "satellite": "A",
        "processingLevel": "L1C",
        "acquisitionYear": "2017",
        "acquisitionMonth": "07",
        "acquisitionDay": "29",
        "utm": "19",
        "lat": "U",
        "sq": "DP",
        "num": "0",
        "scene": "S2A_L1C_20170729_19UDP_0",
        "date": "2017-07-29",
        "_utm": "19",
        "_month": "7",
        "_day": "29",
    }
    assert s2_sceneid_parser(SENTINEL_SCENE_L1) == expected_content


def test_sentinel_newidl2a_valid():
    """Parse sentinel-2 valid sceneid and return metadata."""
    expected_content = {
        "sensor": "2",
        "satellite": "A",
        "processingLevel": "L2A",
        "acquisitionYear": "2017",
        "acquisitionMonth": "07",
        "acquisitionDay": "29",
        "utm": "19",
        "lat": "U",
        "sq": "DP",
        "num": "0",
        "scene": "S2A_L2A_20170729_19UDP_0",
        "date": "2017-07-29",
        "_utm": "19",
        "_month": "7",
        "_day": "29",
    }
    assert s2_sceneid_parser(SENTINEL_SCENE_L2) == expected_content
