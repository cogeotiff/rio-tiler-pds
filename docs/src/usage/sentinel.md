## Sentinel 2 - AWS

### L1C - JPEG2000

!!! warnings

    :warning: JPEG2000 format is not `Cloud Optimized`, numerous GET requests will be needed to read such format
    which could result in important cost.

bands: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

```python
import rasterio
from rio_tiler_pds.sentinel.aws import S2JP2Reader

# We use __enter__ context manager for the Reader.
# When creating the instance of `sentinel` the Reader will fetch the sentinel 2 TileInfo.json
# to retrieve the bounds of the dataset and other metadata available at `sentinel.tileInfo`.
with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with S2JP2Reader("S2A_L1C_20170729_19UDP_0") as sentinel:
        # bounds and metadata are derived from the tileInfo.json file stored with the JPEG2000
        print(type(sentinel))
        >>> <class 'rio_tiler_pds.sentinel.aws.sentinel2.S2L1CReader'>

        print(type(sentinel.tileInfo))
        >>> <class 'dict'>

        print(type(sentinel.datageom))
        >>> <class 'dict'>

        print(sentinel.bands)
        >>> ('B01',
        'B02',
        'B03',
        'B04',
        'B05',
        'B06',
        'B07',
        'B08',
        'B09',
        'B11',
        'B12',
        'B8A')

        print(sentinel.info(bands="B01").json(exclude_none=True))
        >>> {
            'bounds': [-69.98971880792764, 47.761069480166995, -68.86723101847079, 48.75300221903151],
            'minzoom': 8,
            'maxzoom': 14,
            'band_metadata': [["B01", {}]],
            'band_descriptions': [["B01", {}]],
            'dtype': 'uint16',
            'nodata_type': 'Nodata',
            'colorinterp': ['gray']
        }

        print(sentinel.statistics(bands="B8A")["B8A"].json())
        >>> {
            'min': 1.0,
            'max': 19753.0,
            'mean': 2873.8173758756675,
            'count': 653216.0,
            'sum': 1877223491.0,
            'std': 2680.2546389126283,
            'median': 2919.0,
            'majority': 117.0,
            'minority': 9913.0,
            'unique': 11767.0,
            'histogram': [
                [281576.0, 154185.0, 130600.0, 49758.0, 30001.0, 6851.0, 242.0, 1.0, 1.0, 1.0],
                [1.0, 1976.2, 3951.4, 5926.6, 7901.8, 9877.0, 11852.2, 13827.4, 15802.6, 17777.8, 19753.0]
            ],
            'valid_percent': 62.3,
            'masked_pixels': 395360.0,
            'valid_pixels': 653216.0,
            'percentile_98': 9320.699999999953,
            'percentile_2': 106.0
        }

        img = sentinel.tile(77, 89, 8, bands="B01")
        assert img.data.shape == (1, 256, 256)

        print(sentinel.point(-69.41, 48.25, bands=("B01", "B02")))
        >> PointData(
            array=masked_array(data=[1201, 843], mask=[False, False], fill_value=999999, dtype=uint16),
            band_names=['B01', 'B02'],
            coordinates=(-69.41, 48.25),
            crs=CRS.from_epsg(4326),
            assets=[
                's3://sentinel-s2-l1c/tiles/19/U/DP/2017/7/29/0/B01.jp2',
                's3://sentinel-s2-l1c/tiles/19/U/DP/2017/7/29/0/B02.jp2'
            ],
            metadata={}
        )

        # Working with Expression
        img = sentinel.tile(77, 89, 8, expression="B01/B02")
        assert igm.data.shape == (1, 256, 256)

        print(sentinel.point(-69.41, 48.25, expression="B01/B02"))
        >> PointData(
            array=masked_array(data=[1.424673784104389], mask=[False], fill_value=999999, dtype=float32),
            band_names=['B01/B02'],
            coordinates=(-69.41, 48.25),
            crs=CRS.from_epsg(4326),
            assets=[
                's3://sentinel-s2-l1c/tiles/19/U/DP/2017/7/29/0/B01.jp2',
                's3://sentinel-s2-l1c/tiles/19/U/DP/2017/7/29/0/B02.jp2'
            ],
            metadata={}
        )
```

### L2A - JPEG2000

!!! warnings

    :warning: JPEG2000 format is not `Cloud Optimized`, numerous GET requests will be needed to read such format
    which could result in important cost.

bands: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

Note: `AOT, SCL, WVP` bands are not supported.

```python
import rasterio
from rio_tiler_pds.sentinel.aws import S2JP2Reader

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with S2JP2Reader("S2A_L2A_20170729_19UDP_0") as sentinel:
        # bounds and metadata are derived from the tileInfo.json file stored with the JPEG2000
        print(type(sentinel))
        >>> <class 'rio_tiler_pds.sentinel.aws.sentinel2.S2L2AReader'>

        print(type(sentinel.tileInfo))
        >>> dict

        print(type(sentinel.datageom))
        >>> dict

        print(sentinel.info(bands="B01").dict(exclude_none=True))
        >>> {
            "bounds": [-69.98831359398795, 47.7610811323474, -68.86723101847079, 48.75300225264652],
            "minzoom": 8,
            "maxzoom": 14,
            "band_metadata": [["B01", {}]],
            "band_descriptions": [["B01", ""]],
            "dtype": "uint16",
            "nodata_type": "Nodata",
            "colorinterp": ["gray"]
        }
```

### COG (Only L2A available for now)

bands: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

Note: `AOT, SCL, WVP` STAC assets are not supported.

Notes:

- the `B10` band is the cirrus band and is only supported for L1C, not L2A.
- the `sentinel-2-l2a-cogs` is a public dataset, no AWS credential should be needed.

```python
from rio_tiler_pds.sentinel.aws import S2COGReader

with S2COGReader("S2A_29RKH_20200219_0_L2A") as sentinel:
    print(type(sentinel))
    >>> <class 'rio_tiler_pds.sentinel.aws.sentinel2.S2L2ACOGReader'>

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


!!! Important

For most dataset hosted on AWS you will need to have AWS credentials available in your environment.
