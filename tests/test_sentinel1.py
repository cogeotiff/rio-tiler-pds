"""tests rio_tiler_pds.sentinel1"""

import os
from unittest.mock import patch

import pytest
import rasterio

from rio_tiler.errors import InvalidBandName
from rio_tiler_pds.errors import InvalidSentinelSceneId
from rio_tiler_pds.sentinel.aws import S1L1CReader

SENTINEL_SCENE = "S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B"
SENTINEL_BUCKET = os.path.join(os.path.dirname(__file__), "fixtures", "sentinel-s1-l1c")

with open(
    "{}/GRD/2018/7/16/IW/DV/S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B/productInfo.json".format(
        SENTINEL_BUCKET
    ),
    "r",
) as f:
    SENTINEL_METADATA = f.read()


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
    assert band.startswith("s3://sentinel-s1-l1c")
    band = band.replace("s3://sentinel-s1-l1c", SENTINEL_BUCKET)
    return rasterio.open(band)


@patch("rio_tiler_pds.sentinel.aws.sentinel1.get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_S1L1CReader(rio, get_object):
    """Test AWSPDS_S1L1CReader."""
    rio.open = mock_rasterio_open
    get_object.return_value = SENTINEL_METADATA

    with pytest.raises(InvalidSentinelSceneId):
        with S1L1CReader("S2A_tile_20170729_19UDP_0"):
            pass

    with S1L1CReader(SENTINEL_SCENE) as sentinel:
        assert sentinel.scene_params["scene"] == SENTINEL_SCENE
        assert sentinel.minzoom == 8
        assert sentinel.maxzoom == 14
        assert len(sentinel.bounds) == 4
        assert sentinel.bands == ("vv", "vh")

        with pytest.raises(InvalidBandName):
            sentinel.info(bands="B1")

        metadata = sentinel.info(bands="vv")
        assert len(metadata["band_metadata"]) == 1
        assert metadata["band_metadata"][0][0] == "vv"
        assert metadata["band_descriptions"] == [("vv", "")]

        metadata = sentinel.stats(bands=("vv", "vh"))
        assert metadata["vv"]["min"] == 4
        assert metadata["vh"]["max"] == 623

        metadata = sentinel.metadata(bands=("vv", "vh"))
        assert metadata["statistics"]["vv"]["min"] == 4
        assert metadata["statistics"]["vh"]["max"] == 623

        tile_z = 8
        tile_x = 183
        tile_y = 120
        data, mask = sentinel.tile(tile_x, tile_y, tile_z, bands="vv")
        assert data.shape == (1, 256, 256)
        assert mask.shape == (256, 256)

        data, mask = sentinel.tile(tile_x, tile_y, tile_z, bands=("vv", "vh"))
        assert data.shape == (2, 256, 256)
        assert mask.shape == (256, 256)
