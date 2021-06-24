"""tests rio_tiler.sentinel2"""

import os
from unittest.mock import patch

import pytest
import rasterio

from rio_tiler.errors import ExpressionMixingWarning, InvalidBandName, MissingBands
from rio_tiler_pds.errors import InvalidSentinelSceneId
from rio_tiler_pds.sentinel.aws import (
    S2COGReader,
    S2JP2Reader,
    S2L1CReader,
    S2L2ACOGReader,
    S2L2AReader,
)
from rio_tiler_pds.sentinel.utils import s2_sceneid_parser

SENTINEL_SCENE_L1 = "S2A_L1C_20170729_19UDP_0"
SENTINEL_SCENE_L2 = "S2A_L2A_20170729_19UDP_0"
SENTINEL_COG_SCENE_L2 = "S2A_29RKH_20200219_0_L2A"
SENTINEL_COG_PRODUCT = "S2A_MSIL2A_20200219T013442_N0204_R031_T29RKH_20200219T013443"
SENTINEL_PRODUCT = "S2A_MSIL1C_20170105T013442_N0204_R031_T53NMJ_20170105T013443"
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


def mock_rasterio_open(band):
    """Mock rasterio Open for Sentinel2 dataset."""
    assert band.startswith("s3://sentinel-s2-l")
    band = band.replace("s3://sentinel-s2", SENTINEL_BUCKET)
    return rasterio.open(band)


@patch("rio_tiler_pds.sentinel.aws.sentinel2.get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_S2L1CReader(rio, get_object):
    """Test AWSPDS_S2L1CReader."""
    rio.open = mock_rasterio_open
    get_object.return_value = L1C_TILEJSON

    with pytest.raises(InvalidSentinelSceneId):
        with S2L1CReader("S2A_tile_20170323_17SNC"):
            pass

    with S2JP2Reader(SENTINEL_SCENE_L1) as sentinel:
        assert isinstance(sentinel, S2L1CReader)

    with S2L1CReader(SENTINEL_SCENE_L1) as sentinel:
        assert sentinel.scene_params["scene"] == SENTINEL_SCENE_L1
        assert sentinel.minzoom == 8
        assert sentinel.maxzoom == 14
        assert len(sentinel.bounds) == 4
        assert sentinel.bands == (
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
        with pytest.raises(InvalidBandName):
            sentinel.stats(bands="B20")

        assert sentinel._get_band_url("B1") == sentinel._get_band_url("B01")

        values = sentinel.point(-69.41, 48.25, bands=("B01", "B02"))
        assert values == [1193, 846]

        values = sentinel.point(-69.41, 48.25, bands="B01")
        assert values == [1193]

        values = sentinel.point(-69.41, 48.25, expression="B01/B02")
        assert values[0] == 1193.0 / 846.0

        with pytest.raises(MissingBands):
            sentinel.point(-69.41, 48.25)

        with pytest.warns(ExpressionMixingWarning):
            values = sentinel.point(-69.41, 48.25, bands="B01", expression="B01/B02")
            assert values[0] == 1193.0 / 846.0

        stats = sentinel.stats(bands="B01")
        assert stats["B01"]["percentiles"] == [1094, 8170]

        metadata = sentinel.metadata(bands="B01")
        assert metadata["statistics"]["B01"]["percentiles"] == [1094, 8170]

        tile_z = 8
        tile_x = 78
        tile_y = 89
        data, mask = sentinel.tile(tile_x, tile_y, tile_z, bands=("B04", "B03", "B02"))
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)

        with pytest.raises(MissingBands):
            sentinel.tile(tile_x, tile_y, tile_z)

        with pytest.warns(ExpressionMixingWarning):
            data, _ = sentinel.tile(
                tile_x,
                tile_y,
                tile_z,
                bands=("B04", "B03", "B02"),
                expression="B01/B02",
            )
            assert data.shape == (1, 256, 256)

        bbox = (-69.8, 48.2, -69, 48.7)
        data, mask = sentinel.part(bbox, bands="B04")
        assert data.any()
        assert not mask.all()

        data, mask = sentinel.part(bbox, bands=("B04", "B03", "B02"))
        assert data.any()
        assert not mask.all()

        with pytest.raises(MissingBands):
            sentinel.part(bbox)

        with pytest.warns(ExpressionMixingWarning):
            data, _ = sentinel.part(
                bbox, bands=("B04", "B03", "B02"), expression="B01/B02"
            )
            assert data.any()

        # Check for kwargs colision
        # If nodata=None is passed, it will overwrite the default nodata set in the reader
        # https://github.com/cogeotiff/rio-tiler/blob/master/rio_tiler/io/cogeo.py#L277
        data, mask = sentinel.preview(bands="B01", nodata=None)
        assert mask.all()

        with pytest.raises(MissingBands):
            sentinel.preview()

        with pytest.warns(ExpressionMixingWarning):
            data, _ = sentinel.preview(
                bands=("B04", "B03", "B02"), expression="B01/B02"
            )
            assert data.any()


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


@patch("rio_tiler_pds.sentinel.aws.sentinel2.get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_S2L2AReader(rio, get_object):
    """Test AWSPDS_S2L2AReader."""
    rio.open = mock_rasterio_open
    get_object.return_value = L2A_TILEJSON

    with pytest.raises(InvalidSentinelSceneId):
        with S2L1CReader("S2A_tile_20170323_17SNC"):
            pass

    with S2JP2Reader(SENTINEL_SCENE_L2) as sentinel:
        assert isinstance(sentinel, S2L2AReader)

    with S2L2AReader(SENTINEL_SCENE_L2) as sentinel:
        assert sentinel.scene_params["scene"] == SENTINEL_SCENE_L2
        assert sentinel.minzoom == 8
        assert sentinel.maxzoom == 14
        assert len(sentinel.bounds) == 4
        assert sentinel.bands == (
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
            # "AOT",
            # "SCL",
            # "WVP",
        )
        with pytest.raises(InvalidBandName):
            sentinel.stats(bands="B25")

        assert sentinel._get_band_url("B1") == sentinel._get_band_url("B01")

        stats = sentinel.stats(bands="B01")
        assert stats["B01"]["percentiles"] == [1094, 8170]

        metadata = sentinel.metadata(bands="B01")
        assert metadata["statistics"]["B01"]["percentiles"] == [1094, 8170]

        tile_z = 8
        tile_x = 78
        tile_y = 89
        data, mask = sentinel.tile(tile_x, tile_y, tile_z, bands=("B04", "B03", "B02"))
        assert data.shape == (3, 256, 256)
        assert mask.shape == (256, 256)

        assert sentinel._get_resolution("B01") == "60"
        assert sentinel._get_resolution("B02") == "10"
        assert sentinel._get_resolution("B06") == "20"
        assert sentinel._get_resolution("AOT") == "10"
        assert sentinel._get_resolution("SCL") == "20"


L2ACOG_TJSON_PATH = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "sentinel-cogs",
    "sentinel-s2-l2a-cogs",
    "29",
    "R",
    "KH",
    "2020",
    "2",
    SENTINEL_COG_SCENE_L2,
    f"{SENTINEL_COG_SCENE_L2}.json",
)
with open(L2ACOG_TJSON_PATH, "rb") as f:
    L2ACOG_JSON = f.read()


SENTINEL_COG_BUCKET = os.path.join(
    os.path.dirname(__file__), "fixtures", "sentinel-cogs"
)


def mock_rasterio_open_cogs(band):
    """Mock rasterio Open for Sentinel2 dataset."""
    assert band.startswith("s3://sentinel-cogs")
    band = band.replace("s3://sentinel-cogs", SENTINEL_COG_BUCKET)
    return rasterio.open(band)


@patch("rio_tiler_pds.sentinel.aws.sentinel2.get_object")
@patch("rio_tiler.io.cogeo.rasterio")
def test_AWSPDS_S2COGReader(rio, get_object):
    """Test AWSPDS_S2L2ACOGReader."""
    rio.open = mock_rasterio_open_cogs
    get_object.return_value = L2ACOG_JSON

    with pytest.raises(InvalidSentinelSceneId):
        with S2COGReader("S2A_tile_20170323_17SNC"):
            pass

    with S2COGReader(SENTINEL_COG_SCENE_L2) as sentinel:
        assert isinstance(sentinel, S2L2ACOGReader)
        assert sentinel.scene_params["scene"] == SENTINEL_COG_SCENE_L2
        assert sentinel.minzoom == 8
        assert sentinel.maxzoom == 14
        assert len(sentinel.bounds) == 4
        assert sorted(sentinel.bands) == sorted(
            (
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
        )
        with pytest.raises(InvalidBandName):
            sentinel.stats(bands="B30")

        assert sentinel._get_band_url("B1") == sentinel._get_band_url("B01")

        stats = sentinel.stats(bands="B01")
        assert stats["B01"]["percentiles"] == [1029, 1929]

        assert (
            sentinel._get_band_url("B01")
            == "s3://sentinel-cogs/sentinel-s2-l2a-cogs/29/R/KH/2020/2/S2A_29RKH_20200219_0_L2A/B01.tif"
        )

    # Test with legacy Scene id format
    with S2COGReader("S2A_L2A_20200219_29RKH_0") as sentinel:
        assert sentinel.scene_params["scene"] == "S2A_L2A_20200219_29RKH_0"
        assert sentinel.minzoom == 8
        assert sentinel.maxzoom == 14
        assert len(sentinel.bounds) == 4
        assert sorted(sentinel.bands) == sorted(
            (
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
        )
        with pytest.raises(InvalidBandName):
            sentinel.stats(bands="B25")

        stats = sentinel.stats(bands="B01")
        assert stats["B01"]["percentiles"] == [1029, 1929]

        assert (
            sentinel._get_band_url("B01")
            == "s3://sentinel-cogs/sentinel-s2-l2a-cogs/29/R/KH/2020/2/S2A_29RKH_20200219_0_L2A/B01.tif"
        )

    # Test with product ID
    with S2COGReader(SENTINEL_COG_PRODUCT) as sentinel:
        assert sentinel.scene_params["scene"] == SENTINEL_COG_PRODUCT
        assert (
            sentinel._get_band_url("B01")
            == "s3://sentinel-cogs/sentinel-s2-l2a-cogs/29/R/KH/2020/2/S2A_29RKH_20200219_0_L2A/B01.tif"
        )


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
        "scene": SENTINEL_SCENE_L1,
        "date": "2017-07-29",
        "_utm": "19",
        "_month": "7",
        "_day": "29",
        "_levelLow": "l1c",
    }
    assert s2_sceneid_parser(SENTINEL_SCENE_L1) == expected_content


def test_sentinel_newid_valid_single_digit_utm():
    """Parse sentinel-2 valid sceneid and return metadata for single-digit UTM zone."""
    expected_content = {
        "sensor": "2",
        "satellite": "B",
        "processingLevel": "L2A",
        "acquisitionYear": "2018",
        "acquisitionMonth": "10",
        "acquisitionDay": "02",
        "utm": "2",
        "lat": "C",
        "sq": "MA",
        "num": "0",
        "scene": "S2B_2CMA_20181002_0_L2A",
        "date": "2018-10-02",
        "_utm": "2",
        "_month": "10",
        "_day": "2",
        "_levelLow": "l2a",
    }
    assert s2_sceneid_parser("S2B_2CMA_20181002_0_L2A") == expected_content


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
        "scene": SENTINEL_SCENE_L2,
        "date": "2017-07-29",
        "_utm": "19",
        "_month": "7",
        "_day": "29",
        "_levelLow": "l2a",
    }
    assert s2_sceneid_parser(SENTINEL_SCENE_L2) == expected_content


def test_sentinel_newidl2a_valid_double_digit_revisit():
    """Parse sentinel-2 valid sceneid and return metadata."""
    expected_content = {
        "sensor": "2",
        "satellite": "B",
        "processingLevel": "L2A",
        "acquisitionYear": "2019",
        "acquisitionMonth": "05",
        "acquisitionDay": "07",
        "utm": "22",
        "lat": "X",
        "sq": "DL",
        "num": "10",
        "scene": "S2B_22XDL_20190507_10_L2A",
        "date": "2019-05-07",
        "_utm": "22",
        "_month": "5",
        "_day": "7",
        "_levelLow": "l2a",
    }
    assert s2_sceneid_parser("S2B_22XDL_20190507_10_L2A") == expected_content


def test_sentinel_cogid_valid():
    """Parse sentinel-2 COG id valid sceneid and return metadata."""
    expected_content = {
        "sensor": "2",
        "satellite": "A",
        "processingLevel": "L2A",
        "acquisitionYear": "2020",
        "acquisitionMonth": "02",
        "acquisitionDay": "19",
        "utm": "29",
        "lat": "R",
        "sq": "KH",
        "num": "0",
        "scene": SENTINEL_COG_SCENE_L2,
        "date": "2020-02-19",
        "_utm": "29",
        "_month": "2",
        "_day": "19",
        "_levelLow": "l2a",
    }
    assert s2_sceneid_parser(SENTINEL_COG_SCENE_L2) == expected_content


def test_sentinel_productid_valid():
    """Parse sentinel-2 product id valid sceneid and return metadata."""
    expected_content = {
        "sensor": "2",
        "satellite": "A",
        "processingLevel": "L1C",
        "acquisitionYear": "2017",
        "acquisitionMonth": "01",
        "acquisitionDay": "05",
        "acquisitionHMS": "013442",
        "baseline_number": "0204",
        "relative_orbit": "031",
        "utm": "53",
        "lat": "N",
        "sq": "MJ",
        "stopDateTime": "20170105T013443",
        "num": "0",
        "scene": SENTINEL_PRODUCT,
        "date": "2017-01-05",
        "_utm": "53",
        "_month": "1",
        "_day": "5",
        "_levelLow": "l1c",
    }
    assert s2_sceneid_parser(SENTINEL_PRODUCT) == expected_content


def test_no_readers():
    """Test no reader found for level."""
    with pytest.raises(Exception):
        S2JP2Reader("S2B_L1B_20170729_19UDP_0")

    with pytest.raises(Exception):
        S2JP2Reader("S2A_L2C_20170729_19UDP_0")

    with pytest.raises(Exception):
        S2COGReader("S2A_29RKH_20200219_0_L2C")
