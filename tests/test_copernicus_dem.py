"""tests rio_tiler_pds.copernicus"""

import json
import os
from unittest.mock import patch

import morecantile
import pytest
import rasterio
from rasterio.crs import CRS

from rio_tiler_pds.copernicus.aws import Dem30Reader, Dem90Reader

COPERNICUS_30m_BUCKET = os.path.join(
    os.path.dirname(__file__), "fixtures", "copernicus-dem-30m"
)
COPERNICUS_90m_BUCKET = os.path.join(
    os.path.dirname(__file__), "fixtures", "copernicus-dem-90m"
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


def mock_rasterio_open(src_path):
    """Mock rasterio Open."""
    if src_path.startswith("s3://copernicus-dem-30m"):
        src_path = src_path.replace("s3://copernicus-dem-30m", COPERNICUS_30m_BUCKET)
        return rasterio.open(src_path)

    elif src_path.startswith("s3://copernicus-dem-90m"):
        src_path = src_path.replace("s3://copernicus-dem-90m", COPERNICUS_90m_BUCKET)
        return rasterio.open(src_path)

    else:
        raise ValueError(f"Invalid path {src_path}")


@patch("rio_tiler.io.rasterio.rasterio")
def test_Dem30Reader(rio):
    """Test Dem30Reader."""
    rio.open = mock_rasterio_open

    with Dem30Reader() as dem:
        assert dem.input == "copernicus-dem-30m"
        assert dem.minzoom == 7
        assert dem.maxzoom == 8
        assert dem.bounds == (-180, -90, 180, 90)
        assert dem.get_geographic_bounds(CRS.from_epsg(4326)) == (-180, -90, 180, 90)

        info = dem.info()
        assert info.bounds == dem.bounds
        crs = info.crs
        assert CRS.from_user_input(crs) == dem.crs

        assert dem.statistics()["b1"]

        assert dem._get_dataset_url(0, 0).endswith(
            "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif"
        )
        assert dem._get_dataset_url(1, 1).endswith(
            "Copernicus_DSM_COG_10_N01_00_E001_00_DEM.tif"
        )
        assert dem._get_dataset_url(-1, -1).endswith(
            "Copernicus_DSM_COG_10_S01_00_W001_00_DEM.tif"
        )

        pts = dem.assets_for_point(0, 0)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif")

        pts = dem.assets_for_point(9.9, 9.9)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_10_N09_00_E009_00_DEM.tif")

        pts = dem.assets_for_point(10.1, 10.1)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_10_N10_00_E010_00_DEM.tif")

        pts = dem.assets_for_point(-9.9, -9.9)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_10_S10_00_W010_00_DEM.tif")

        pts = dem.assets_for_point(-10.1, -10.1)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_10_S11_00_W011_00_DEM.tif")

        pts = dem.assets_for_point(10, 10)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_10_N10_00_E010_00_DEM.tif")

        pts = dem.assets_for_point(1113194.91, 1118889.98, coord_crs="epsg:3857")
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_10_N10_00_E010_00_DEM.tif")

        bbox = dem.assets_for_bbox(10, 10, 11, 11)
        assert len(bbox) == 4
        assert bbox[0].endswith("Copernicus_DSM_COG_10_N10_00_E010_00_DEM.tif")
        assert bbox[1].endswith("Copernicus_DSM_COG_10_N11_00_E010_00_DEM.tif")
        assert bbox[2].endswith("Copernicus_DSM_COG_10_N10_00_E011_00_DEM.tif")
        assert bbox[3].endswith("Copernicus_DSM_COG_10_N11_00_E011_00_DEM.tif")

        bbox = dem.assets_for_bbox(
            1113194.91,
            1118889.98,
            1224514.39,
            1232106.80,
            coord_crs="epsg:3857",
        )
        assert len(bbox) == 1
        assert bbox[0].endswith("Copernicus_DSM_COG_10_N10_00_E010_00_DEM.tif")

        tile = dem.assets_for_tile(530, 509, 10)
        assert len(tile) == 2

        img = dem.tile(1060, 1019, 11)
        assert img.array.shape == (1, 256, 256)
        assert img.crs == "epsg:3857"

        pts = dem.point(6.2, 0.1)
        assert pts.array.shape == (1,)
        assert pts.assets[0].endswith("Copernicus_DSM_COG_10_N00_00_E006_00_DEM.tif")

    tms = morecantile.tms.get("WGS1984Quad")
    with Dem30Reader(tms=tms) as dem:
        tile = dem.assets_for_tile(1062, 510, 10)
        assert len(tile) == 1

        img = dem.tile(1062, 510, 10)
        assert img.array.shape == (1, 256, 256)
        assert img.crs == "epsg:4326"


@patch("rio_tiler.io.rasterio.rasterio")
def test_Dem90Reader(rio):
    """Test Dem90Reader."""
    rio.open = mock_rasterio_open

    with Dem90Reader() as dem:
        assert dem.input == "copernicus-dem-90m"
        assert dem.minzoom == 6
        assert dem.maxzoom == 7
        assert dem.bounds == (-180, -90, 180, 90)
        assert dem.get_geographic_bounds(CRS.from_epsg(4326)) == (-180, -90, 180, 90)

        info = dem.info()
        assert info.bounds == dem.bounds
        crs = info.crs
        assert CRS.from_user_input(crs) == dem.crs

        assert dem.statistics()["b1"]

        assert dem._get_dataset_url(0, 0).endswith(
            "Copernicus_DSM_COG_30_N00_00_E000_00_DEM.tif"
        )
        assert dem._get_dataset_url(1, 1).endswith(
            "Copernicus_DSM_COG_30_N01_00_E001_00_DEM.tif"
        )
        assert dem._get_dataset_url(-1, -1).endswith(
            "Copernicus_DSM_COG_30_S01_00_W001_00_DEM.tif"
        )

        pts = dem.assets_for_point(0, 0)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_30_N00_00_E000_00_DEM.tif")

        pts = dem.assets_for_point(9.9, 9.9)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_30_N09_00_E009_00_DEM.tif")

        pts = dem.assets_for_point(10.1, 10.1)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_30_N10_00_E010_00_DEM.tif")

        pts = dem.assets_for_point(-9.9, -9.9)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_30_S10_00_W010_00_DEM.tif")

        pts = dem.assets_for_point(-10.1, -10.1)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_30_S11_00_W011_00_DEM.tif")

        pts = dem.assets_for_point(10, 10)
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_30_N10_00_E010_00_DEM.tif")

        pts = dem.assets_for_point(1113194.91, 1118889.98, coord_crs="epsg:3857")
        assert len(pts) == 1
        assert pts[0].endswith("Copernicus_DSM_COG_30_N10_00_E010_00_DEM.tif")

        bbox = dem.assets_for_bbox(10, 10, 11, 11)
        assert len(bbox) == 4
        assert bbox[0].endswith("Copernicus_DSM_COG_30_N10_00_E010_00_DEM.tif")
        assert bbox[1].endswith("Copernicus_DSM_COG_30_N11_00_E010_00_DEM.tif")
        assert bbox[2].endswith("Copernicus_DSM_COG_30_N10_00_E011_00_DEM.tif")
        assert bbox[3].endswith("Copernicus_DSM_COG_30_N11_00_E011_00_DEM.tif")

        bbox = dem.assets_for_bbox(
            1113194.91,
            1118889.98,
            1224514.39,
            1232106.80,
            coord_crs="epsg:3857",
        )
        assert len(bbox) == 1
        assert bbox[0].endswith("Copernicus_DSM_COG_30_N10_00_E010_00_DEM.tif")

        tile = dem.assets_for_tile(530, 509, 10)
        assert len(tile) == 2

        pts = dem.point(-163.9, -89.5)
        assert pts.array.shape == (1,)
        assert pts.assets[0].endswith("Copernicus_DSM_COG_30_S90_00_W164_00_DEM.tif")
