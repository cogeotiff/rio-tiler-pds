
# Usage

## Sentinel 2 - AWS

### L1C - JPEG2000

bands: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

```python
import rasterio
from rio_tiler_pds.sentinel.aws import S2L1CReader

# We use __enter__ context manager for the Reader.
# When creating the instance of `sentinel` the Reader will fetch the sentinel 2 TileInfo.json
# to retrieve the bounds of the dataset and other metadata available at `sentinel.tileInfo`.
with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with S2L1CReader("S2A_L1C_20170729_19UDP_0") as sentinel:
        # bounds and metadata are derived from the tileInfo.json file stored with the JPEG2000
        print(type(sentinel.tileInfo))
        >>> dict

        print(type(sentinel.datageom))
        >>> dict

        print(sentinel.center)
        >>> (-69.4190338105916, 48.25699850457617, 8)

        print(sentinel.info(bands="B01").dict(exclude_none=True))
        >>> {
            'bounds': (-69.97083660271242, 47.761069480166974, -68.86723101847078, 48.75292752898536),
            'center': (-69.4190338105916, 48.25699850457617, 8),
            'minzoom': 8,
            'maxzoom': 14,
            'band_metadata': [('B01', {})],
            'band_descriptions': [('B01', '')],
            'dtype': 'uint16',
            'colorinterp': ['gray'],
            'nodata_type': 'None'
        }

        print(sentinel.stats(bands="B8A")["B8A"].dict())
        >>> {
            'percentiles': [106, 9322],
            'min': 1,
            'max': 13659,
            'std': 2682.6511198930048,
            'histogram': [
                [261631, 52188, 137746, 98039, 41066, 30818, 21095, 8631, 1442, 105],
                [1.0, 1366.8, 2732.6, 4098.4, 5464.2, 6830.0, 8195.8, 9561.6, 10927.4, 12293.199999999999, 13659.0]
            ]
        }

        img = sentinel.tile(77, 89, 8, bands="B01")
        assert img.data.shape == (1, 256, 256)

        print(sentinel.point(-69.41, 48.25, bands=("B01", "B02")))
        # Result is in form of
        # [
        #   value for band 1 in band B01,
        #   value for band 1 in band B02
        # ]
        > [1230, 875]

        # Working with Expression
        img = sentinel.tile(77, 89, 8, expression="B01/B02")
        assert igm.data.shape == (1, 256, 256)

        print(sentinel.point(-69.41, 48.25, expression="B01/B02"))
        > [1.424673784104389]
```

### L2A - JPEG2000

bands: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

Note: `AOT, SCL, WVP` bands are not supported.

```python
import rasterio
from rio_tiler_pds.sentinel.aws import S2L2AReader

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with S2L2AReader("S2A_L2A_20170729_19UDP_0") as sentinel:
        # bounds and metadata are derived from the tileInfo.json file stored with the JPEG2000
        print(type(sentinel.tileInfo))
        >>> dict

        print(type(sentinel.datageom))
        >>> dict

        print(sentinel.info(bands="B01").dict(exclude_none=True))
        >>> {
            'bounds': (-69.96945818759949, 47.7610811323474, -68.86723101847078, 48.75292752898536),
            'center': (-69.41834460303514, 48.257004330666376, 8),
            'minzoom': 8,
            'maxzoom': 14,
            'band_metadata': [('B01', {})],
            'band_descriptions': [('B01', '')],
            'dtype': 'uint16',
            'colorinterp': ['gray'],
            'nodata_type': 'None'
        }
```

### COG (Only L2A available for now)

bands: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

Note: `AOT, SCL, WVP` STAC assets are not supported.

```python
from rio_tiler_pds.sentinel.aws import S2COGReader

with S2COGReader("S2A_29RKH_20200219_0_L2A") as sentinel:
    print(sentinel.bands)
    >>> ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A')

    # bounds and metadata are derived from the STAC item stored with the COG
    print(type(sentinel.stac_item))
    >>> dict
```

## Sentinel 1 - AWS

```python
import rasterio
from rio_tiler_pds.sentinel.aws import S1L1CReader

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with S1L1CReader("S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B") as sentinel:
        print(sentinel.bands)
        > ('vv', 'vh')

        print(sentine.bounds)
        > (75.605247, 9.225784, 78.203903, 11.190425)

        print(type(sentinel.productInfo))
        > dict

        print(sentinel._get_band_url("vv"))
        > 's3://sentinel-s1-l1c/GRD/2018/7/16/IW/DV/S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B/measurement/iw-vv.tiff'
```

## Landsat 8 - AWS

Landsat 8 dataset hosted on AWS are not a proper Cloud Optimized GeoTIFF because they have external overviews. To make sure the performance is good enough and limit the number of LIST/GET requests from GDAL/Rasterio, we can set some environment variables:

```bash
# https://trac.osgeo.org/gdal/wiki/ConfigOptions#CPL_VSIL_CURL_ALLOWED_EXTENSIONS
CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.TIF,.ovr

# https://trac.osgeo.org/gdal/wiki/ConfigOptions#GDAL_DISABLE_READDIR_ON_OPEN
GDAL_DISABLE_READDIR_ON_OPEN=FALSE
```

You can either set those variables in your environment or within your code using `rasterio.Env()`.

```python
import rasterio
from rio_tiler_pds.landsat.aws import L8Reader

with rasterio.Env(
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".TIF,.ovr",
    GDAL_DISABLE_READDIR_ON_OPEN="FALSE",
):
    with L8Reader("LC08_L1TP_016037_20170813_20170814_01_RT") as landsat:
        print(landsat.bands)
        >>> ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'BQA'
        assert landsat.minzoom == 7
        assert landsat.minzoom == 12

        print(landsat.spatial_info.dict())
        >>> {
          'bounds': (-81.30836, 32.10539, -78.82045, 34.22818),
          'center': (-80.064405, 33.166785000000004, 7),
          'minzoom': 7,
          'maxzoom': 12
        }

        print(landsat.info(bands="B1").dict(exclude_none=True))
        >>> {
          'bounds': (-81.30836, 32.10539, -78.82045, 34.22818),
          'center': (-80.064405, 33.166785000000004, 7),
          'minzoom': 7,
          'maxzoom': 12,
          'band_metadata': [('B1', {})],
          'band_descriptions': [('B1', '')],
          'dtype': 'uint16',
          'colorinterp': ['gray'],
          'nodata_type': 'None'
        }

        print(landsat.stats(bands="B1")["B1"].dict())
        > {
            'percentiles': [1207, 6989],
            'min': 922,
            'max': 13512,
            'std': 297,
            'histogram': [
              [574527, 54320, 37316, 25318, 15086, 8101, 3145, 744, 160, 21],
              [922, 2181, 3440, 4699, 5958, 7217, 8476, 9735, 10994, 12253, 13512]
            ]
        }

        tile_z = 8
        tile_x = 71
        tile_y = 102
        img = landsat.tile(tile_x, tile_y, tile_z, bands=("B4", "B3", "B2"))
        assert img.data.shape == (3, 256, 256)

        img = landsat.tile(tile_x, tile_y, tile_z, bands="B10")
        assert img.data.shape == (1, 256, 256)

       img = landsat.tile(
            tile_x, tile_y, tile_z, bands=("B4", "B3", "B2"), pan=True
        )
        assert img.data.shape == (3, 256, 256)

        img = landsat.tile(
            tile_x, tile_y, tile_z, expression="B5*0.8, B4*1.1, B3*0.8"
        )
        assert img.data.shape == (3, 256, 256)

        img = landsat.preview(
            bands=("B4", "B3", "B2"), pan=True, width=256, height=256
        )
        assert img.data.shape == (3, 256, 256)
```

## CBERS 4 - AWS

```python
from rio_tiler_pds.cbers.aws import CBERSReader

CBERS_MUX_SCENE = "CBERS_4_MUX_20171121_057_094_L2"
CBERS_AWFI_SCENE = "CBERS_4_AWFI_20170420_146_129_L2"
CBERS_PAN10M_SCENE = "CBERS_4_PAN10M_20170427_161_109_L4"
CBERS_PAN5M_SCENE = "CBERS_4_PAN5M_20170425_153_114_L4"


with CBERSReader("CBERS_4_MUX_20171121_057_094_L2") as cbers:
    print(cbers.bands)
    >>> ('B5', 'B6', 'B7', 'B8')

    print(cbers.bounds)
    >>> (53.302020833057796, 4.756472757234311, 54.628483877373, 6.025171883475984)

    assert cbers.minzoom == 8
    assert cbers.maxzoom == 12

with CBERSReader("CBERS_4_AWFI_20170420_146_129_L2") as cbers:
    print(cbers.bands)
    >>> ('B13', 'B14', 'B15', 'B16')

with CBERSReader("CBERS_4_PAN10M_20170427_161_109_L4") as cbers:
    print(cbers.bands)
    >>> ('B2', 'B3', 'B4')


with CBERSReader("CBERS_4_PAN5M_20170425_153_114_L4") as cbers:
    print(cbers.bands)
    >>> ('B1',)
```

## MODIS - AWS

### PDS (modis-pds bucket)

**Products**: MCD43A4, MOD09GQ, MYD09GQ, MOD09GA, MYD09GA

```python
from rio_tiler_pds.modis.aws import MODISPDSReader

MCD43A4_SCENE = "MCD43A4.A2017006.h21v11.006.2017018074804"
with MODISPDSReader(MCD43A4_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B01qa", "B02", "B02qa", "B03", "B03qa", "B04", "B04qa", "B05", "B05qa", "B06", "B06qa", "B07", "B07qa")

    print(modis.bounds)
    >>> (31.9253, -30.0, 46.1976, -20.0)

    assert modis.minzoom == 4
    assert modis.maxzoom == 9

MOD09GA_SCENE = "MOD09GA.A2017129.h34v07.006.2017137214839"
with MODISPDSReader(MOD09GA_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "geoflags", "granule", "numobs1km", "numobs500m", "obscov", "obsnum", "orbit", "qc500m", "qscan", "range", "senaz", "senzen", "solaz", "solzen", "state")

MOD09GQ_SCENE = "MOD09GQ.A2017120.h29v09.006.2017122031126"
with MODISPDSReader(MOD09GQ_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B02", "granule", "numobs", "obscov", "obsnum", "orbit", "qc")
```

### ASTRAEA (astraea-opendata bucket)

**Products**: MCD43A4, MOD11A1, MOD13A1, MYD11A1 MYD13A1

```python
from rio_tiler_pds.modis.aws import MODISASTRAEAReader

MCD43A4_SCENE = "MCD43A4.A2017006.h21v11.006.2017018074804"
with MODISASTRAEAReader(MCD43A4_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B01qa", "B02", "B02qa", "B03", "B03qa", "B04", "B04qa", "B05", "B05qa", "B06", "B06qa", "B07", "B07qa")

    print(modis.bounds)
    >>> (31.9253, -30.0, 46.1976, -20.0)

    assert modis.minzoom == 4
    assert modis.maxzoom == 9

MOD11A1_SCENE = "MOD11A1.A2020250.h20v11.006.2020251085003"
with MODISASTRAEAReader(MOD11A1_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12")

MOD13A1_SCENE = "MOD13A1.A2020049.h14v04.006.2020066002045"
with MODISASTRAEAReader(MOD13A1_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12")
```

## Requester-Pays

Some data are stored on AWS requester-pays buckets (you are charged for LIST/GET requests and data transfer outside the bucket region). For those datasets you need to set `AWS_REQUEST_PAYER="requester"` environement variable to tell AWS S3 that you agree with requester-pays principle.

You can either set those variables in your environment or within your code using `rasterio.Env()`.

```python
import rasterio
from rio_tiler_pds.sentinel.aws import S2L1CReader

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with S2L1CReader("S2A_L1C_20170729_19UDP_0") as s2:
        print(s2.preview(bands="B01", width=64, height=64))
```
