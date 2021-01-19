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
        # ('QA_PIXEL', 'QA_RADSAT', 'SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'SR_QA_AEROSOL')
        assert landsat.minzoom == 5
        assert landsat.maxzoom == 12

        print(landsat.spatial_info.dict())
        # {'bounds': (127.5491501485206,
        #             -66.70704040042727,
        #             132.96321916779596,
        #             -64.45548178742538),
        #  'center': (130.25618465815828, -65.58126109392633, 5),
        #  'maxzoom': 12,
        #  'minzoom': 5}

        print(landsat.info(bands="SR_B1").dict(exclude_none=True))
        # {'band_descriptions': [('SR_B1', '')],
        #  'band_metadata': [('SR_B1', {})],
        #  'bounds': (127.5491501485206,
        #             -66.70704040042727,
        #             132.96321916779596,
        #             -64.45548178742538),
        #  'center': (130.25618465815828, -65.58126109392633, 5),
        #  'colorinterp': ['gray'],
        #  'dtype': 'uint16',
        #  'maxzoom': 12,
        #  'minzoom': 5,
        #  'nodata_type': 'Nodata'}

        print(landsat.stats(bands="SR_B1")["SR_B1"].dict())
        # {'histogram': [[6580.0,
        #                 291951.0,
        #                 35705.0,
        #                 30246.0,
        #                 21644.0,
        #                 14611.0,
        #                 22435.0,
        #                 33499.0,
        #                 46199.0,
        #                 53017.0],
        #                [5.0,
        #                 5587.0,
        #                 11169.0,
        #                 16751.0,
        #                 22333.0,
        #                 27915.0,
        #                 33497.0,
        #                 39079.0,
        #                 44661.0,
        #                 50243.0,
        #                 55825.0]],
        #  'max': 55825.0,
        #  'min': 5.0,
        #  'percentiles': [6223.0, 52240.0],
        #  'std': 16839.923244537837}

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
