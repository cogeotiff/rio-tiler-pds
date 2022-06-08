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
        assert landsat.maxzoom == 12

        print(landsat.info(bands="B1").json(exclude_none=True))
        >>> {
          "bounds": [-81.30836, 32.10539, -78.82045, 34.22818],
          "minzoom": 7,
          "maxzoom": 12,
          "band_metadata": [["B1", {}]],
          "band_descriptions": [["B1", ""]],
          "dtype": "uint16",
          "nodata_type": "Nodata",
          "colorinterp": ["gray"]
        }

        print(landsat.statistics(bands="B1")["B1"].json())
        >>> {
          "min": 0.0,
          "max": 11930.0,
          "mean": 2033.7163353188776,
          "count": 721045.0,
          "sum": 1466400995.0,
          "std": 1342.4201622910466,
          "median": 1491.0,
          "majority": 0.0,
          "minority": 11.0,
          "unique": 9363.0,
          "histogram": [
            [9259.0, 574137.0, 60257.0, 33983.0, 20278.0, 12212.0, 7189.0, 2999.0, 641.0, 90.0],
            [0.0, 1193.0, 2386.0, 3579.0, 4772.0, 5965.0, 7158.0, 8351.0, 9544.0, 10737.0, 11930.0]
          ],
          "valid_percent": 69.99,
          "masked_pixels": 309099.0,
          "valid_pixels": 721045.0,
          "percentile_98": 6757.0,
          "percentile_2": 1212.0
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
