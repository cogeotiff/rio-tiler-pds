"""tests rio_tiler.landsat8"""

import os
from unittest.mock import patch

import numpy
import pytest
import rasterio

from rio_tiler.errors import InvalidBandName, MissingBands, TileOutsideBounds
from rio_tiler_pds.errors import InvalidLandsatSceneId
from rio_tiler_pds.landsat.aws import L8Reader
from rio_tiler_pds.landsat.utils import (
    OLI_L1_BANDS,
    OLI_L1_QA_BANDS,
    TIRS_L1_BANDS,
    sceneid_parser,
)

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


def mock_rasterio_open(band):
    """Mock rasterio Open."""
    assert band.startswith("s3://landsat-pds")
    band = band.replace("s3://landsat-pds", LANDSAT_BUCKET)
    return rasterio.open(band)


@patch("rio_tiler_pds.landsat.aws.landsat8.get_object")
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
        assert landsat.bands == (
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

        with pytest.raises(MissingBands):
            landsat.info()

        with pytest.raises(InvalidBandName):
            landsat.info(bands="BAND5")

        metadata = landsat.info(bands="B5")
        assert len(metadata["band_metadata"]) == 1
        assert metadata["band_descriptions"] == [("B5", "")]

        metadata = landsat.info(bands=landsat.bands)
        assert len(metadata["band_metadata"]) == 12

        with pytest.raises(MissingBands):
            landsat.stats()

        stats = landsat.stats(bands="B1")
        assert stats["B1"]["percentiles"] == [1206, 6957]

        stats = landsat.stats(bands=landsat.bands)
        assert len(stats.items()) == 12
        assert list(stats) == list(landsat.bands)

        stats = landsat.stats(bands="B1", hist_options=dict(bins=20))
        assert len(stats["B1"]["histogram"][0]) == 20

        stats = landsat.stats(pmin=10, pmax=90, bands="B1")
        assert stats["B1"]["percentiles"] == [1274, 3964]

        stats = landsat.stats(bands="BQA")
        assert stats["BQA"]["min"] == 2720

        stats = landsat.stats(bands="BQA", nodata=0, resampling_method="bilinear")
        # nodata and resampling_method are set at reader level an shouldn't be set
        assert stats["BQA"]["min"] == 1

        with pytest.raises(MissingBands):
            landsat.metadata()

        metadata = landsat.metadata(bands="B1")
        assert metadata["statistics"]["B1"]["percentiles"] == [1206, 6957]
        assert metadata["band_metadata"] == [("B1", {})]
        assert metadata["band_descriptions"] == [("B1", "")]

        metadata = landsat.metadata(bands=("B1", "B2"))
        assert metadata["band_metadata"] == [("B1", {}), ("B2", {})]
        assert metadata["band_descriptions"] == [("B1", ""), ("B2", "")]

        # nodata and resampling_method are set at reader level an shouldn't be set
        metadata = landsat.metadata(bands="BQA", nodata=0, resampling_method="bilinear")
        assert metadata["statistics"]["BQA"]["min"] == 1

        tile_z = 8
        tile_x = 71
        tile_y = 102

        with pytest.raises(MissingBands):
            landsat.tile(tile_x, tile_y, tile_z)

        data, mask = landsat.tile(tile_x, tile_y, tile_z, bands=("B4", "B3", "B2"))
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)
        assert not mask.all()

        # Temp are float32
        data, mask = landsat.tile(tile_x, tile_y, tile_z, bands="B10")
        assert data.shape == (1, 256, 256)
        assert data.dtype == numpy.float32
        assert mask.shape == (256, 256)

        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, bands="BQA", nodata=0, resampling_method="bilinear"
        )
        assert data.shape == (1, 256, 256)
        assert not mask.all()

        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, bands=("B4", "B3", "B2"), pan=True
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)

        tile_z = 8
        tile_x = 701
        tile_y = 102
        with pytest.raises(TileOutsideBounds):
            landsat.tile(tile_x, tile_y, tile_z, bands=("B4", "B3", "B2"))

        tile_z = 8
        tile_x = 71
        tile_y = 102
        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, expression="B5*0.8, B4*1.1, B3*0.8"
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.float64
        assert mask.shape == (256, 256)

        with pytest.raises(MissingBands):
            landsat.preview()

        data, mask = landsat.preview(bands=("B4", "B3", "B2"))
        assert data.shape == (3, 259, 255)
        assert data.dtype == numpy.uint16
        assert mask.shape == (259, 255)
        assert not mask.all()

        # Temp are float32
        data, mask = landsat.preview(bands="B10")
        assert data.shape == (1, 259, 255)
        assert data.dtype == numpy.float32
        assert mask.shape == (259, 255)

        data, mask = landsat.preview(
            bands=("B4", "B3", "B2"), pan=True, width=256, height=256
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)

        data, mask = landsat.preview(expression="B5*0.8, B4*1.1, B3*0.8")
        assert data.shape == (3, 259, 255)
        assert data.dtype == numpy.float64
        assert mask.shape == (259, 255)

        data, mask = landsat.preview(bands="BQA")
        assert data.shape == (1, 259, 255)
        assert not mask.all()

        # nodata and resampling_method are set at reader level an shouldn't be set
        data, mask = landsat.preview(
            bands="BQA", nodata=0, resampling_method="bilinear"
        )
        assert data.shape == (1, 259, 255)
        assert mask.all()

        with pytest.raises(MissingBands):
            landsat.point(-80.094, 33.2062)

        values = landsat.point(-80.094, 33.2062, bands="B7")
        assert values == [667]

        values = landsat.point(-80.094, 33.2062, bands="BQA")
        assert values[0] == 2800

        values = landsat.point(-80.094, 33.2062, bands=("B7", "B4"))
        assert len(values) == 2

        values = landsat.point(-80.094, 33.2062, expression="B5*0.8, B4*1.1, B3*0.8")
        assert len(values) == 3

        with pytest.raises(MissingBands):
            landsat.part((-80.593, 32.9134, -79.674, 33.6790))

        data, mask = landsat.part((-80.593, 32.9134, -79.674, 33.6790), bands="B7")
        assert data.shape == (1, 87, 104)
        assert data.dtype == numpy.uint16
        assert mask.shape == (87, 104)
        assert mask.all()

        data, _ = landsat.part(
            (-80.593, 32.9134, -79.674, 33.6790),
            bands="BQA",
            nodata=0,
            resampling_method="bilinear",
        )
        assert data.shape == (1, 87, 104)

        data, mask = landsat.part(
            (-80.593, 32.9134, -79.674, 33.6790), expression="B5*0.8, B4*1.1, B3*0.8"
        )
        assert data.shape == (3, 87, 104)
        assert data.dtype == numpy.float64
        assert mask.shape == (87, 104)
        assert mask.all()

        data, mask = landsat.part(
            (-80.593, 32.9134, -79.674, 33.6790),
            bands=("B4", "B3", "B2"),
            pan=True,
            width=80,
            height=80,
        )
        assert data.shape == (3, 80, 80)
        assert data.dtype == numpy.uint16
        assert mask.shape == (80, 80)

        feat = {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-80.1397705078125, 32.63937487360669],
                        [-79.6453857421875, 32.63937487360669],
                        [-79.6453857421875, 32.94875863715422],
                        [-80.1397705078125, 32.94875863715422],
                        [-80.1397705078125, 32.63937487360669],
                    ]
                ],
            },
        }
        with pytest.raises(MissingBands):
            landsat.feature(feat)

        data, mask = landsat.feature(feat, bands="B7")
        assert data.shape == (1, 35, 56)
        assert data.dtype == numpy.uint16
        assert mask.shape == (35, 56)

        data, _ = landsat.feature(
            feat, bands="BQA", nodata=0, resampling_method="bilinear",
        )
        assert data.shape == (1, 35, 56)

        data, mask = landsat.feature(feat, expression="B5*0.8, B4*1.1, B3*0.8")
        assert data.shape == (3, 35, 56)
        assert data.dtype == numpy.float64
        assert mask.shape == (35, 56)

        data, mask = landsat.feature(
            feat, bands=("B4", "B3", "B2"), pan=True, width=80, height=80,
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
        "_processingLevelNum": "1",
        "sensor_name": "oli-tirs",
        "_sensor_s3_prefix": "oli-tirs",
        "bands": OLI_L1_BANDS + TIRS_L1_BANDS + OLI_L1_QA_BANDS,
    }

    assert sceneid_parser(scene) == expected_content
