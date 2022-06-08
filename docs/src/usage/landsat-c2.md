## Landsat Collection 2 - AWS

In late 2020, the U.S. Geological Survey (USGS) — the organization that
publishes Landsat data — released Landsat Collection 2. This is a major
reprocessing of the entire Landsat archive. All Landsat data in Collection 2 is
now stored as Cloud-Optimized GeoTIFF (COG)!

[landsat_c2]: https://www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2

Landsat Collection 2 can be accessed directly from an AWS bucket. The USGS maintains the `usgs-landsat` S3 bucket. Keys under the `s3://usgs-landsat/collection02/` prefix are publicly accessible. Note that this bucket is a [requester-pays][aws_requester_pays] bucket, which means that the costs of accessing the data accrue to the _user_, not the _host_.

[aws_requester_pays]: https://docs.aws.amazon.com/AmazonS3/latest/dev/RequesterPaysBuckets.html

Since data are requester pays, we need to set an environment variable to access the data through `rasterio`.

```bash
AWS_REQUEST_PAYER="requester"
```

You can either set those variables in your environment or within your code using `rasterio.Env()`.

```python
import rasterio
from rio_tiler_pds.landsat.aws import LandsatC2Reader

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with LandsatC2Reader("LC08_L2SR_093106_20200207_20201016_02_T2") as landsat:
        print(landsat.bands)
        >>> ('QA_PIXEL', 'QA_RADSAT', 'SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'SR_QA_AEROSOL')
        assert landsat.minzoom == 5
        assert landsat.maxzoom == 12

        print(landsat.info(bands="SR_B1").json(exclude_none=True))
        >>> {
            "bounds": [127.54909041630796, -66.70705179185323, 132.96277753047164, -64.4554629843337],
            "minzoom": 5,
            "maxzoom": 12,
            "band_metadata": [["SR_B1", {}]],
            "band_descriptions": [["SR_B1", ""]],
            "dtype": "uint16",
            "nodata_type": "Nodata",
            "colorinterp": ["gray"]
        }

        print(landsat.statistics(bands="SR_B1")["SR_B1"].json())
        >>> {
            "min": 2487.0,
            "max": 53345.0,
            "mean": 21039.126798561152,
            "count": 8896.0,
            "sum": 187164072.0,
            "std": 16484.450981447077,
            "median": 10978.0,
            "majority": 8233.0,
            "minority": 2487.0,
            "unique": 5932.0,
            "histogram": [
                [594.0, 4181.0, 603.0, 557.0, 296.0, 207.0, 296.0, 469.0, 615.0, 1078.0],
                [2487.0, 7572.8, 12658.6, 17744.4, 22830.2, 27916.0, 33001.8, 38087.6, 43173.4, 48259.200000000004, 53345.0]
            ],
            "valid_percent": 54.3,
            "masked_pixels": 7488.0,
            "valid_pixels": 8896.0,
            "percentile_98": 52178.1,
            "percentile_2": 7367.9
        }

        tile_z = 8
        tile_x = 218
        tile_y = 188
        img = landsat.tile(tile_x, tile_y, tile_z, bands=("SR_B4", "SR_B3", "SR_B2"))
        assert img.data.shape == (3, 256, 256)

        img = landsat.tile(tile_x, tile_y, tile_z, bands="SR_B5")
        assert img.data.shape == (1, 256, 256)

        img = landsat.tile(
            tile_x, tile_y, tile_z, expression="SR_B5*0.8, SR_B4*1.1, SR_B3*0.8"
        )
        assert img.data.shape == (3, 256, 256)

        img = landsat.preview(
            bands=("SR_B4", "SR_B3", "SR_B2"), pan=True, width=256, height=256
        )
        assert img.data.shape == (3, 256, 256)
```
