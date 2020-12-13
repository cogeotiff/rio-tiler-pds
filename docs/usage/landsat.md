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
