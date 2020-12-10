from pathlib import Path
from unittest.mock import patch

import numpy
import pytest
import rasterio

from rio_tiler.errors import InvalidBandName, MissingBands, TileOutsideBounds
from rio_tiler_pds.errors import InvalidLandsatSceneId
from rio_tiler_pds.landsat.aws import LandsatC2L2Reader
from rio_tiler_pds.landsat.aws.landsat_collection2 import (OLI_TIRS_SR_BANDS,
                                                           OLI_TIRS_ST_BANDS)
from rio_tiler_pds.landsat.utils import sceneid_parser

# sceneid,expected_content
LANDSAT_SCENE_PARSER_TEST_CASES = (
    # Collection 2 Level 2 OLI-TIRS 8 SP (both SR and ST)
    (
        "LC08_L2SP_001062_20201031_20201106_02_T2",
        {
            "sensor": "C",
            "satellite": "08",
            "processingCorrectionLevel": "L2SP",
            "path": "001",
            "row": "062",
            "acquisitionYear": "2020",
            "acquisitionMonth": "10",
            "acquisitionDay": "31",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "06",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LC08_L2SP_001062_20201031_20201106_02_T2",
            "date": "2020-10-31",
            "_processingLevelNum": "2",
            "_sensor": "oli-tirs",
        },
    ),
    # Collection 2 Level 2 OLI-TIRS 8 SR (no ST)
    (
        "LC08_L2SR_122108_20201031_20201106_02_T2",
        {
            "sensor": "C",
            "satellite": "08",
            "processingCorrectionLevel": "L2SR",
            "path": "122",
            "row": "108",
            "acquisitionYear": "2020",
            "acquisitionMonth": "10",
            "acquisitionDay": "31",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "06",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LC08_L2SR_122108_20201031_20201106_02_T2",
            "date": "2020-10-31",
            "_processingLevelNum": "2",
            "_sensor": "oli-tirs",
        },
    ),
    # Collection 2 Level 2 TM SP (both SR and ST)
    (
        "LT05_L2SP_014032_20111018_20200820_02_T1",
        {
            "sensor": "T",
            "satellite": "05",
            "processingCorrectionLevel": "L2SP",
            "path": "014",
            "row": "032",
            "acquisitionYear": "2011",
            "acquisitionMonth": "10",
            "acquisitionDay": "18",
            "processingYear": "2020",
            "processingMonth": "08",
            "processingDay": "20",
            "collectionNumber": "02",
            "collectionCategory": "T1",
            "scene": "LT05_L2SP_014032_20111018_20200820_02_T1",
            "date": "2011-10-18",
            "_processingLevelNum": "2",
            "_sensor": "tm",
        },
    ),
    # Collection 2 Level 2 TM SR (no ST)
    (
        "LT05_L2SR_089076_20110929_20200820_02_T2",
        {
            "sensor": "T",
            "satellite": "05",
            "processingCorrectionLevel": "L2SR",
            "path": "089",
            "row": "076",
            "acquisitionYear": "2011",
            "acquisitionMonth": "09",
            "acquisitionDay": "29",
            "processingYear": "2020",
            "processingMonth": "08",
            "processingDay": "20",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LT05_L2SR_089076_20110929_20200820_02_T2",
            "date": "2011-09-29",
            "_processingLevelNum": "2",
            "_sensor": "tm",
        },
    ),
    # Collection 2 Level 2 ETM SP (both SR and ST)
    (
        "LE07_L2SP_175066_20201026_20201121_02_T1",
        {
            "sensor": "E",
            "satellite": "07",
            "processingCorrectionLevel": "L2SP",
            "path": "175",
            "row": "066",
            "acquisitionYear": "2020",
            "acquisitionMonth": "10",
            "acquisitionDay": "26",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "21",
            "collectionNumber": "02",
            "collectionCategory": "T1",
            "scene": "LE07_L2SP_175066_20201026_20201121_02_T1",
            "date": "2020-10-26",
            "_processingLevelNum": "2",
            "_sensor": "etm",
        },
    ),
    # Collection 2 Level 2 ETM SR (no ST)
    (
        "LE07_L2SR_123067_20201030_20201126_02_T1",
        {
            "sensor": "E",
            "satellite": "07",
            "processingCorrectionLevel": "L2SR",
            "path": "123",
            "row": "067",
            "acquisitionYear": "2020",
            "acquisitionMonth": "10",
            "acquisitionDay": "30",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "26",
            "collectionNumber": "02",
            "collectionCategory": "T1",
            "scene": "LE07_L2SR_123067_20201030_20201126_02_T1",
            "date": "2020-10-30",
            "_processingLevelNum": "2",
            "_sensor": "etm",
        },
    ),
)


@pytest.mark.parametrize("sceneid,expected_content", LANDSAT_SCENE_PARSER_TEST_CASES)
def test_landsat_sceneid_parser(sceneid, expected_content):
    """Parse landsat valid collection1 sceneid and return metadata."""
    assert sceneid_parser(sceneid) == expected_content


LANDSAT_SCENE_C2 = "LC08_L2SP_001062_20201031_20201106_02_T2"
LANDSAT_BUCKET = Path(__file__).resolve().parent / 'fixtures' / 'usgs-landsat'
LANDSAT_PATH = (LANDSAT_BUCKET / "collection02" / "level-2" / "standard" / "oli-tirs" / "2020" / "001" / "062" / LANDSAT_SCENE_C2)
INVALID_LANDSAT_SCENE_C2 = 'LC08_001062_20201031_20201106_02_T2'

with open(LANDSAT_PATH / f"{LANDSAT_SCENE_C2}_SR_stac.json", "r") as f:
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
    assert band.startswith("s3://usgs-landsat")
    band = band.replace("s3://usgs-landsat", str(LANDSAT_BUCKET))
    return rasterio.open(band)


@patch("rio_tiler_pds.landsat.aws.landsat_collection2.get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_LandsatC2L2Reader(rio, get_object):
    """Should work as expected (get and parse metadata)."""
    rio.open = mock_rasterio_open
    get_object.return_value = LANDSAT_METADATA

    with pytest.raises(InvalidLandsatSceneId):
        with LandsatC2L2Reader(INVALID_LANDSAT_SCENE_C2):
            pass

    with LandsatC2L2Reader(LANDSAT_SCENE_C2) as landsat:
        assert landsat.scene_params["scene"] == LANDSAT_SCENE_C2
        assert landsat.minzoom == 5
        assert landsat.maxzoom == 12
        assert len(landsat.bounds) == 4
        assert landsat.bands == OLI_TIRS_SR_BANDS + OLI_TIRS_ST_BANDS

        with pytest.raises(MissingBands):
            landsat.info()

        with pytest.raises(InvalidBandName):
            landsat.info(bands="BAND5")

        metadata = landsat.info(bands="SR_B5")
        assert len(metadata["band_metadata"]) == 1
        assert metadata["band_descriptions"] == [("SR_B5", "")]

        metadata = landsat.info(bands=landsat.bands)
        assert len(metadata["band_metadata"]) == len(OLI_TIRS_SR_BANDS + OLI_TIRS_ST_BANDS)

        with pytest.raises(MissingBands):
            landsat.stats()

        stats = landsat.stats(bands="SR_B1")
        assert stats["SR_B1"]["percentiles"] == [7926, 49017]

        stats = landsat.stats(bands=landsat.bands)
        assert len(stats.items()) == len(OLI_TIRS_SR_BANDS + OLI_TIRS_ST_BANDS)
        assert list(stats) == list(landsat.bands)

        stats = landsat.stats(bands="SR_B1", hist_options=dict(bins=20))
        assert len(stats["SR_B1"]["histogram"][0]) == 20

        stats = landsat.stats(pmin=10, pmax=90, bands="SR_B1")
        assert stats["SR_B1"]["percentiles"] == [8524, 43038]

        stats = landsat.stats(bands="QA_PIXEL")
        assert stats["QA_PIXEL"]["min"] == 1

        stats = landsat.stats(bands="QA_PIXEL", nodata=0, resampling_method="bilinear")
        # nodata and resampling_method are set at reader level an shouldn't be set
        assert stats["QA_PIXEL"]["min"] == 1

        with pytest.raises(MissingBands):
            landsat.metadata()

        metadata = landsat.metadata(bands="SR_B1")
        assert metadata["statistics"]["SR_B1"]["percentiles"] == [7926, 49017]
        assert metadata["band_metadata"] == [("SR_B1", {})]
        assert metadata["band_descriptions"] == [("SR_B1", "")]

        metadata = landsat.metadata(bands=("SR_B1", "SR_B2"))
        assert metadata["band_metadata"] == [("SR_B1", {}), ("SR_B2", {})]
        assert metadata["band_descriptions"] == [("SR_B1", ""), ("SR_B2", "")]

        # nodata and resampling_method are set at reader level an shouldn't be set
        metadata = landsat.metadata(bands="QA_PIXEL", nodata=0, resampling_method="bilinear")
        assert metadata["statistics"]["QA_PIXEL"]["min"] == 1

        tile_z = 8
        tile_x = 71
        tile_y = 102

        with pytest.raises(MissingBands):
            landsat.tile(tile_x, tile_y, tile_z)

        data, mask = landsat.tile(tile_x, tile_y, tile_z, bands=("SR_B4", "SR_B3", "SR_B2"))
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)
        assert not mask.all()

        # Temp are float32
        data, mask = landsat.tile(tile_x, tile_y, tile_z, bands="SR_B10")
        assert data.shape == (1, 256, 256)
        assert data.dtype == numpy.float32
        assert mask.shape == (256, 256)

        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, bands="QA_PIXEL", nodata=0, resampling_method="bilinear"
        )
        assert data.shape == (1, 256, 256)
        assert not mask.all()

        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, bands=("SR_B4", "SR_B3", "SR_B2"), pan=True
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)

        tile_z = 8
        tile_x = 701
        tile_y = 102
        with pytest.raises(TileOutsideBounds):
            landsat.tile(tile_x, tile_y, tile_z, bands=("SR_B4", "SR_B3", "SR_B2"))

        tile_z = 8
        tile_x = 71
        tile_y = 102
        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8"
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.float64
        assert mask.shape == (256, 256)

        with pytest.raises(MissingBands):
            landsat.preview()

        data, mask = landsat.preview(bands=("SR_B4", "SR_B3", "SR_B2"))
        assert data.shape == (3, 259, 255)
        assert data.dtype == numpy.uint16
        assert mask.shape == (259, 255)
        assert not mask.all()

        # Temp are float32
        data, mask = landsat.preview(bands="SR_B10")
        assert data.shape == (1, 259, 255)
        assert data.dtype == numpy.float32
        assert mask.shape == (259, 255)

        data, mask = landsat.preview(
            bands=("SR_B4", "SR_B3", "SR_B2"), pan=True, width=256, height=256
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)

        data, mask = landsat.preview(expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8")
        assert data.shape == (3, 259, 255)
        assert data.dtype == numpy.float64
        assert mask.shape == (259, 255)

        data, mask = landsat.preview(bands="QA_PIXEL")
        assert data.shape == (1, 259, 255)
        assert not mask.all()

        # nodata and resampling_method are set at reader level an shouldn't be set
        data, mask = landsat.preview(
            bands="QA_PIXEL", nodata=0, resampling_method="bilinear"
        )
        assert data.shape == (1, 259, 255)
        assert mask.all()

        with pytest.raises(MissingBands):
            landsat.point(-80.094, 33.2062)

        values = landsat.point(-80.094, 33.2062, bands="SR_B7")
        assert values == [667]

        values = landsat.point(-80.094, 33.2062, bands="QA_PIXEL")
        assert values[0] == 2800

        values = landsat.point(-80.094, 33.2062, bands=("SR_B7", "SR_B4"))
        assert len(values) == 2

        values = landsat.point(-80.094, 33.2062, expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8")
        assert len(values) == 3

        with pytest.raises(MissingBands):
            landsat.part((-80.593, 32.9134, -79.674, 33.6790))

        data, mask = landsat.part((-80.593, 32.9134, -79.674, 33.6790), bands="SR_B7")
        assert data.shape == (1, 87, 104)
        assert data.dtype == numpy.uint16
        assert mask.shape == (87, 104)
        assert mask.all()

        data, _ = landsat.part(
            (-80.593, 32.9134, -79.674, 33.6790),
            bands="QA_PIXEL",
            nodata=0,
            resampling_method="bilinear",
        )
        assert data.shape == (1, 87, 104)

        data, mask = landsat.part(
            (-80.593, 32.9134, -79.674, 33.6790), expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8"
        )
        assert data.shape == (3, 87, 104)
        assert data.dtype == numpy.float64
        assert mask.shape == (87, 104)
        assert mask.all()

        data, mask = landsat.part(
            (-80.593, 32.9134, -79.674, 33.6790),
            bands=("SR_B4", "SR_B3", "SR_B2"),
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

        data, mask = landsat.feature(feat, bands="SR_B7")
        assert data.shape == (1, 35, 56)
        assert data.dtype == numpy.uint16
        assert mask.shape == (35, 56)

        data, _ = landsat.feature(
            feat, bands="QA_PIXEL", nodata=0, resampling_method="bilinear",
        )
        assert data.shape == (1, 35, 56)

        data, mask = landsat.feature(feat, expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8")
        assert data.shape == (3, 35, 56)
        assert data.dtype == numpy.float64
        assert mask.shape == (35, 56)

        data, mask = landsat.feature(
            feat, bands=("SR_B4", "SR_B3", "SR_B2"), pan=True, width=80, height=80,
        )
        assert data.shape == (3, 80, 80)
        assert data.dtype == numpy.uint16
        assert mask.shape == (80, 80)
