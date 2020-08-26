"""tests rio_tiler.landsat8"""

import os
from unittest.mock import patch

import numpy
import pytest
import rasterio

from rio_tiler.errors import InvalidAssetName, MissingAssets, TileOutsideBounds
from rio_tiler_pds.errors import InvalidLandsatSceneId
from rio_tiler_pds.landsat.aws import L8Reader
from rio_tiler_pds.landsat.utils import sceneid_parser

LANDSAT_SCENE_C1 = "LC08_L1TP_016037_20170813_20170814_01_RT"
LANDSAT_BUCKET = os.path.join(os.path.dirname(__file__), "fixtures", "landsat-pds")
LANDSAT_PATH = os.path.join(
    LANDSAT_BUCKET, "c1", "L8", "016", "037", LANDSAT_SCENE_C1, LANDSAT_SCENE_C1
)

with open("{}_MTL.txt".format(LANDSAT_PATH), "r") as f:
    LANDSAT_METADATA = f.read().encode("utf-8")


@pytest.fixture(autouse=True)
def testing_env_var(monkeypatch):
    """Set fake env to make sure we don't hit AWS services."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "jqt")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "rde")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", "/tmp/noconfigheere")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "/tmp/noconfighereeither")
    monkeypatch.setenv("GDAL_DISABLE_READDIR_ON_OPEN", "TRUE")


def mock_rasterio_open(asset):
    """Mock rasterio Open."""
    assert asset.startswith("s3://landsat-pds")
    asset = asset.replace("s3://landsat-pds", LANDSAT_BUCKET)
    return rasterio.open(asset)


@patch("rio_tiler_pds.reader.aws_get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_L8Reader(rio, get_object):
    """Should work as expected (get and parse metadata)."""
    rio.open = mock_rasterio_open
    get_object.return_value = LANDSAT_METADATA

    with pytest.raises(InvalidLandsatSceneId):
        with L8Reader("LC08_005004_20170410_20170414_01_T1"):
            pass

    with L8Reader(LANDSAT_SCENE_C1) as landsat:
        assert landsat.scene_params["scene"] == LANDSAT_SCENE_C1
        assert landsat.minzoom == 7
        assert landsat.maxzoom == 12
        assert len(landsat.bounds) == 4
        assert landsat.assets == (
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

        with pytest.raises(MissingAssets):
            landsat.info()

        with pytest.raises(InvalidAssetName):
            landsat.info(assets="BAND5")

        metadata = landsat.info(assets="B5")
        assert len(metadata["band_metadata"]) == 1
        assert metadata["band_descriptions"] == [(1, "B5")]

        metadata = landsat.info(assets=landsat.assets)
        assert len(metadata["band_metadata"]) == 12

        with pytest.raises(MissingAssets):
            landsat.stats()

        stats = landsat.stats(assets="B1")
        assert stats["B1"]["pc"] == [1206, 6957]

        stats = landsat.stats(assets=landsat.assets)
        assert len(stats.items()) == 12
        assert list(stats) == list(landsat.assets)

        stats = landsat.stats(assets="B1", hist_options=dict(bins=20))
        assert len(stats["B1"]["histogram"][0]) == 20

        stats = landsat.stats(pmin=10, pmax=90, assets="B1")
        assert stats["B1"]["pc"] == [1274, 3964]

        with pytest.raises(MissingAssets):
            landsat.metadata()

        metadata = landsat.metadata(assets="B1")
        assert metadata["statistics"]["B1"]["pc"] == [1206, 6957]
        assert metadata["band_metadata"] == [(1, {})]
        assert metadata["band_descriptions"] == [(1, "B1")]

        metadata = landsat.metadata(assets=("B1", "B2"))
        assert metadata["band_metadata"] == [(1, {}), (2, {})]
        assert metadata["band_descriptions"] == [(1, "B1"), (2, "B2")]

        tile_z = 8
        tile_x = 71
        tile_y = 102

        with pytest.raises(MissingAssets):
            landsat.tile(tile_x, tile_y, tile_z)

        data, mask = landsat.tile(tile_x, tile_y, tile_z, assets=("B4", "B3", "B2"))
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)
        assert not mask.all()

        # Temp are float32
        data, mask = landsat.tile(tile_x, tile_y, tile_z, assets="B10")
        assert data.shape == (1, 256, 256)
        assert data.dtype == numpy.float32
        assert mask.shape == (256, 256)

        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, assets=("B4", "B3", "B2"), pan=True
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)

        tile_z = 8
        tile_x = 701
        tile_y = 102
        with pytest.raises(TileOutsideBounds):
            landsat.tile(tile_x, tile_y, tile_z, assets=("B4", "B3", "B2"))

        tile_z = 8
        tile_x = 71
        tile_y = 102
        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, expression="B5*0.8, B4*1.1, B3*0.8"
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.float64
        assert mask.shape == (256, 256)

        with pytest.raises(MissingAssets):
            landsat.preview()

        data, mask = landsat.preview(assets=("B4", "B3", "B2"))
        assert data.shape == (3, 259, 255)
        assert data.dtype == numpy.uint16
        assert mask.shape == (259, 255)
        assert not mask.all()

        # Temp are float32
        data, mask = landsat.preview(assets="B10")
        assert data.shape == (1, 259, 255)
        assert data.dtype == numpy.float32
        assert mask.shape == (259, 255)

        data, mask = landsat.preview(
            assets=("B4", "B3", "B2"), pan=True, width=256, height=256
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)

        data, mask = landsat.preview(expression="B5*0.8, B4*1.1, B3*0.8")
        assert data.shape == (3, 259, 255)
        assert data.dtype == numpy.float64
        assert mask.shape == (259, 255)

        with pytest.raises(MissingAssets):
            landsat.point(-80.094, 33.2062)

        values = landsat.point(-80.094, 33.2062, assets="B7")
        assert values == [667]

        values = landsat.point(-80.094, 33.2062, assets=("B7", "B4"))
        assert len(values) == 2

        values = landsat.point(-80.094, 33.2062, expression="B5*0.8, B4*1.1, B3*0.8")
        assert len(values) == 3

        with pytest.raises(MissingAssets):
            landsat.part((-80.593, 32.9134, -79.674, 33.6790))

        data, mask = landsat.part((-80.593, 32.9134, -79.674, 33.6790), assets="B7")
        assert data.shape == (1, 87, 104)
        assert data.dtype == numpy.uint16
        assert mask.shape == (87, 104)
        assert mask.all()

        data, mask = landsat.part(
            (-80.593, 32.9134, -79.674, 33.6790), expression="B5*0.8, B4*1.1, B3*0.8"
        )
        assert data.shape == (3, 87, 104)
        assert data.dtype == numpy.float64
        assert mask.shape == (87, 104)
        assert mask.all()

        data, mask = landsat.part(
            (-80.593, 32.9134, -79.674, 33.6790),
            assets=("B4", "B3", "B2"),
            pan=True,
            width=80,
            height=80,
        )
        assert data.shape == (3, 80, 80)
        assert data.dtype == numpy.uint16
        assert mask.shape == (80, 80)


def test_landsat_id_c1_valid():
    """Parse landsat valid collection1 sceneid and return metadata."""
    scene = "LC08_L1TP_005004_20170410_20170414_01_T1"
    expected_content = {
        "sensor": "C",
        "satellite": "08",
        "processingCorrectionLevel": "L1TP",
        "path": "005",
        "row": "004",
        "acquisitionYear": "2017",
        "acquisitionMonth": "04",
        "acquisitionDay": "10",
        "processingYear": "2017",
        "processingMonth": "04",
        "processingDay": "14",
        "collectionNumber": "01",
        "collectionCategory": "T1",
        "scene": "LC08_L1TP_005004_20170410_20170414_01_T1",
        "date": "2017-04-10",
    }

    assert sceneid_parser(scene) == expected_content
