from pathlib import Path
from unittest.mock import patch

import numpy
import pytest
import rasterio

from rio_tiler.errors import InvalidBandName, MissingBands, TileOutsideBounds
from rio_tiler_pds.errors import InvalidLandsatSceneId
from rio_tiler_pds.landsat.aws import LandsatC2Reader
from rio_tiler_pds.landsat.utils import (
    ETM_L1_BANDS,
    MSS_L1_BANDS,
    OLI_SR_BANDS,
    TIRS_ST_BANDS,
    TM_L1_BANDS,
    TM_SR_BANDS,
    TM_ST_BANDS,
    sceneid_parser,
)

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
            "sensor_name": "oli-tirs",
            "bands": OLI_SR_BANDS + TIRS_ST_BANDS,
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
            "sensor_name": "oli-tirs",
            "bands": OLI_SR_BANDS,
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
            "sensor_name": "tm",
            "bands": TM_SR_BANDS + TM_ST_BANDS,
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
            "sensor_name": "tm",
            "bands": TM_SR_BANDS,
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
            "sensor_name": "etm",
            "bands": TM_SR_BANDS + TM_ST_BANDS,
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
            "sensor_name": "etm",
            "bands": TM_SR_BANDS,
        },
    ),
    # Collection 2 Level 1 ETM, L1GS
    (
        "LE07_L1GS_189036_20201129_20201129_02_RT",
        {
            "sensor": "E",
            "satellite": "07",
            "processingCorrectionLevel": "L1GS",
            "path": "189",
            "row": "036",
            "acquisitionYear": "2020",
            "acquisitionMonth": "11",
            "acquisitionDay": "29",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "29",
            "collectionNumber": "02",
            "collectionCategory": "RT",
            "scene": "LE07_L1GS_189036_20201129_20201129_02_RT",
            "date": "2020-11-29",
            "_processingLevelNum": "1",
            "sensor_name": "etm",
            "bands": ETM_L1_BANDS,
        },
    ),
    # Collection 2 Level 1 ETM, L1GT
    (
        "LE07_L1GT_023046_20201204_20201206_02_RT",
        {
            "sensor": "E",
            "satellite": "07",
            "processingCorrectionLevel": "L1GT",
            "path": "023",
            "row": "046",
            "acquisitionYear": "2020",
            "acquisitionMonth": "12",
            "acquisitionDay": "04",
            "processingYear": "2020",
            "processingMonth": "12",
            "processingDay": "06",
            "collectionNumber": "02",
            "collectionCategory": "RT",
            "scene": "LE07_L1GT_023046_20201204_20201206_02_RT",
            "date": "2020-12-04",
            "_processingLevelNum": "1",
            "sensor_name": "etm",
            "bands": ETM_L1_BANDS,
        },
    ),
    # Collection 2 Level 1 ETM, L1TP
    (
        "LE07_L1TP_030042_20201205_20201205_02_RT",
        {
            "sensor": "E",
            "satellite": "07",
            "processingCorrectionLevel": "L1TP",
            "path": "030",
            "row": "042",
            "acquisitionYear": "2020",
            "acquisitionMonth": "12",
            "acquisitionDay": "05",
            "processingYear": "2020",
            "processingMonth": "12",
            "processingDay": "05",
            "collectionNumber": "02",
            "collectionCategory": "RT",
            "scene": "LE07_L1TP_030042_20201205_20201205_02_RT",
            "date": "2020-12-05",
            "_processingLevelNum": "1",
            "sensor_name": "etm",
            "bands": ETM_L1_BANDS,
        },
    ),
    # Collection 2 Level 1 TM, L1GS
    (
        "LT05_L1GS_127054_20111111_20200820_02_T2",
        {
            "sensor": "T",
            "satellite": "05",
            "processingCorrectionLevel": "L1GS",
            "path": "127",
            "row": "054",
            "acquisitionYear": "2011",
            "acquisitionMonth": "11",
            "acquisitionDay": "11",
            "processingYear": "2020",
            "processingMonth": "08",
            "processingDay": "20",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LT05_L1GS_127054_20111111_20200820_02_T2",
            "date": "2011-11-11",
            "_processingLevelNum": "1",
            "sensor_name": "tm",
            "bands": TM_L1_BANDS,
        },
    ),
    # Collection 2 Level 1 TM, L1TP
    (
        "LT05_L1TP_014032_20111018_20200820_02_T1",
        {
            "sensor": "T",
            "satellite": "05",
            "processingCorrectionLevel": "L1TP",
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
            "scene": "LT05_L1TP_014032_20111018_20200820_02_T1",
            "date": "2011-10-18",
            "_processingLevelNum": "1",
            "sensor_name": "tm",
            "bands": TM_L1_BANDS,
        },
    ),
    # Collection 2 Level 1 MSS, L1GS
    (
        "LM05_L1GS_176025_20120901_20200820_02_T2",
        {
            "sensor": "M",
            "satellite": "05",
            "processingCorrectionLevel": "L1GS",
            "path": "176",
            "row": "025",
            "acquisitionYear": "2012",
            "acquisitionMonth": "09",
            "acquisitionDay": "01",
            "processingYear": "2020",
            "processingMonth": "08",
            "processingDay": "20",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LM05_L1GS_176025_20120901_20200820_02_T2",
            "date": "2012-09-01",
            "_processingLevelNum": "1",
            "sensor_name": "mss",
            "bands": MSS_L1_BANDS,
        },
    ),
    # Collection 2 Level 1 MSS, L1TP
    (
        "LM05_L1TP_015032_20121230_20200820_02_T2",
        {
            "sensor": "M",
            "satellite": "05",
            "processingCorrectionLevel": "L1TP",
            "path": "015",
            "row": "032",
            "acquisitionYear": "2012",
            "acquisitionMonth": "12",
            "acquisitionDay": "30",
            "processingYear": "2020",
            "processingMonth": "08",
            "processingDay": "20",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LM05_L1TP_015032_20121230_20200820_02_T2",
            "date": "2012-12-30",
            "_processingLevelNum": "1",
            "sensor_name": "mss",
            "bands": MSS_L1_BANDS,
        },
    ),
)


@pytest.mark.parametrize("sceneid,expected_content", LANDSAT_SCENE_PARSER_TEST_CASES)
def test_landsat_sceneid_parser(sceneid, expected_content):
    """Parse landsat valid collection1 sceneid and return metadata."""
    assert sceneid_parser(sceneid) == expected_content


LANDSAT_SCENE_C2 = "LC08_L2SP_001062_20201031_20201106_02_T2"
LANDSAT_BUCKET = Path(__file__).resolve().parent / "fixtures" / "usgs-landsat"
LANDSAT_PATH = (
    LANDSAT_BUCKET
    / "collection02"
    / "level-2"
    / "standard"
    / "oli-tirs"
    / "2020"
    / "001"
    / "062"
    / LANDSAT_SCENE_C2
)
INVALID_LANDSAT_SCENE_C2 = "LC08_001062_20201031_20201106_02_T2"

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
        with LandsatC2Reader(INVALID_LANDSAT_SCENE_C2):
            pass

    with LandsatC2Reader(LANDSAT_SCENE_C2) as landsat:
        assert landsat.scene_params["scene"] == LANDSAT_SCENE_C2
        assert landsat.minzoom == 5
        assert landsat.maxzoom == 12
        assert len(landsat.bounds) == 4
        assert landsat.bands == OLI_SR_BANDS + TIRS_ST_BANDS

        with pytest.raises(MissingBands):
            landsat.info()

        with pytest.raises(InvalidBandName):
            landsat.info(bands="BAND5")

        metadata = landsat.info(bands="SR_B5")
        assert len(metadata["band_metadata"]) == 1
        assert metadata["band_descriptions"] == [("SR_B5", "")]

        metadata = landsat.info(bands=landsat.bands)
        assert len(metadata["band_metadata"]) == len(OLI_SR_BANDS + TIRS_ST_BANDS)

        with pytest.raises(MissingBands):
            landsat.stats()

        stats = landsat.stats(bands="SR_B1")
        assert stats["SR_B1"]["percentiles"] == [7926, 49017]

        stats = landsat.stats(bands=landsat.bands)
        assert len(stats.items()) == len(OLI_SR_BANDS + TIRS_ST_BANDS)
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
        metadata = landsat.metadata(
            bands="QA_PIXEL", nodata=0, resampling_method="bilinear"
        )
        assert metadata["statistics"]["QA_PIXEL"]["min"] == 1

        tile_z = 8
        tile_x = 81
        tile_y = 130

        with pytest.raises(MissingBands):
            landsat.tile(tile_x, tile_y, tile_z)

        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, bands=("SR_B4", "SR_B3", "SR_B2")
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)
        assert not mask.all()

        # Level 2 collection 2 temperatures are uint16
        data, mask = landsat.tile(tile_x, tile_y, tile_z, bands="ST_B10")
        assert data.shape == (1, 256, 256)
        assert data.dtype == numpy.uint16
        assert mask.shape == (256, 256)

        data, mask = landsat.tile(
            tile_x,
            tile_y,
            tile_z,
            bands="QA_PIXEL",
            nodata=0,
            resampling_method="bilinear",
        )
        assert data.shape == (1, 256, 256)
        assert not mask.all()

        # Pansharpening not yet implemented
        # data, mask = landsat.tile(
        #     tile_x, tile_y, tile_z, bands=("SR_B4", "SR_B3", "SR_B2"), pan=True
        # )
        # assert data.shape == (3, 256, 256)
        # assert data.dtype == numpy.uint16
        # assert mask.shape == (256, 256)

        with pytest.raises(TileOutsideBounds):
            landsat.tile(701, 102, 8, bands=("SR_B4", "SR_B3", "SR_B2"))

        data, mask = landsat.tile(
            tile_x, tile_y, tile_z, expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8"
        )
        assert data.shape == (3, 256, 256)
        assert data.dtype == numpy.float64
        assert mask.shape == (256, 256)

        with pytest.raises(MissingBands):
            landsat.preview()

        data, mask = landsat.preview(bands=("SR_B4", "SR_B3", "SR_B2"))
        assert data.shape == (3, 386, 379)
        assert data.dtype == numpy.uint16
        assert mask.shape == (386, 379)
        assert not mask.all()

        # Level 2 collection 2 temperatures are uint16
        data, mask = landsat.preview(bands="ST_B10")
        assert data.shape == (1, 386, 379)
        assert data.dtype == numpy.uint16
        assert mask.shape == (386, 379)

        # Pansharpening not yet implemented
        # data, mask = landsat.preview(
        #     bands=("SR_B4", "SR_B3", "SR_B2"), pan=True, width=256, height=256
        # )
        # assert data.shape == (3, 256, 256)
        # assert data.dtype == numpy.uint16
        # assert mask.shape == (256, 256)

        data, mask = landsat.preview(expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8")
        assert data.shape == (3, 386, 379)
        assert data.dtype == numpy.float64
        assert mask.shape == (386, 379)

        data, mask = landsat.preview(bands="QA_PIXEL")
        assert data.shape == (1, 386, 379)
        assert mask.all()

        # nodata and resampling_method are set at reader level an shouldn't be set
        data, mask = landsat.preview(
            bands="QA_PIXEL", nodata=0, resampling_method="bilinear"
        )
        assert data.shape == (1, 386, 379)
        assert mask.all()

        bbox = landsat.bounds
        point_x = (bbox[0] + bbox[2]) / 2
        point_y = (bbox[1] + bbox[3]) / 2

        with pytest.raises(MissingBands):
            landsat.point(point_x, point_y)

        values = landsat.point(point_x, point_y, bands="SR_B7")
        assert values == [16414]

        values = landsat.point(point_x, point_y, bands="QA_PIXEL")
        assert values[0] == 22280

        values = landsat.point(point_x, point_y, bands=("SR_B7", "SR_B4"))
        assert len(values) == 2

        values = landsat.point(
            point_x, point_y, expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8"
        )
        assert len(values) == 3

        bbox = landsat.bounds
        minx = (bbox[0] + bbox[2]) * 0.25
        miny = (bbox[1] + bbox[3]) * 0.25
        maxx = (bbox[0] + bbox[2]) * 0.75
        maxy = (bbox[1] + bbox[3]) * 0.75
        part = (minx, miny, maxx, maxy)

        with pytest.raises(MissingBands):
            landsat.part(part)

        data, mask = landsat.part(part, bands="SR_B7")
        assert data.shape == (1, 46, 1024)
        assert data.dtype == numpy.uint16
        assert mask.shape == (46, 1024)
        assert not mask.all()

        data, _ = landsat.part(
            part, bands="QA_PIXEL", nodata=0, resampling_method="bilinear",
        )
        assert data.shape == (1, 46, 1024)

        data, mask = landsat.part(part, expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8")
        assert data.shape == (3, 46, 1024)
        assert data.dtype == numpy.float64
        assert mask.shape == (46, 1024)
        assert not mask.all()

        data, mask = landsat.part(
            part, bands=("SR_B4", "SR_B3", "SR_B2"), width=80, height=80,
        )
        assert data.shape == (3, 80, 80)
        assert data.dtype == numpy.uint16
        assert mask.shape == (80, 80)

        ll = (minx, miny)
        lr = (maxx, miny)
        ul = (minx, maxy)
        ur = (maxx, maxy)

        feat = {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[ll, lr, ur, ul, ll]]},
        }
        with pytest.raises(MissingBands):
            landsat.feature(feat)

        data, mask = landsat.feature(feat, bands="SR_B7")
        assert data.shape == (1, 46, 1024)
        assert data.dtype == numpy.uint16
        assert mask.shape == (46, 1024)

        data, _ = landsat.feature(
            feat, bands="QA_PIXEL", nodata=0, resampling_method="bilinear",
        )
        assert data.shape == (1, 46, 1024)

        data, mask = landsat.feature(feat, expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8")
        assert data.shape == (3, 46, 1024)
        assert data.dtype == numpy.float64
        assert mask.shape == (46, 1024)

        data, mask = landsat.feature(
            feat, bands=("SR_B4", "SR_B3", "SR_B2"), width=80, height=80,
        )
        assert data.shape == (3, 80, 80)
        assert data.dtype == numpy.uint16
        assert mask.shape == (80, 80)


C2_SENSOR_TEST_CASES = [
    # Collection 2 Level 2 OLI-TIRS 8 SP (both SR and ST)
    ("LC08_L2SP_001062_20201031_20201106_02_T2", OLI_SR_BANDS + TIRS_ST_BANDS),
    # Collection 2 Level 2 OLI-TIRS 8 SR (no ST)
    ("LC08_L2SR_122108_20201031_20201106_02_T2", OLI_SR_BANDS),
    # Collection 2 Level 2 TM SP (both SR and ST)
    ("LT05_L2SP_014032_20111018_20200820_02_T1", TM_SR_BANDS + TM_ST_BANDS),
    # Collection 2 Level 2 TM SR (no ST)
    ("LT05_L2SR_089076_20110929_20200820_02_T2", TM_SR_BANDS),
    # Collection 2 Level 2 ETM SP (both SR and ST)
    ("LE07_L2SP_175066_20201026_20201121_02_T1", TM_SR_BANDS + TM_ST_BANDS),
    # Collection 2 Level 2 ETM SR (no ST)
    ("LE07_L2SR_123067_20201030_20201126_02_T1", TM_SR_BANDS),
]


@patch("rio_tiler_pds.landsat.aws.landsat_collection2.get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_LandsatC2L2Reader_bands(rio, get_object):
    """Should work as expected (get and parse metadata)."""
    rio.open = mock_rasterio_open
    get_object.return_value = LANDSAT_METADATA

    with pytest.raises(InvalidLandsatSceneId):
        with LandsatC2Reader(INVALID_LANDSAT_SCENE_C2):
            pass

    for sceneid, expected_bands in C2_SENSOR_TEST_CASES:
        with LandsatC2Reader(sceneid) as landsat:
            assert landsat.bands == expected_bands
