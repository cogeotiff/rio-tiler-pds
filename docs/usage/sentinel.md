## Sentinel 2 - AWS

### L1C - JPEG2000

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

Note: the `B10` band is the cirrus band and is only supported for L1C, not L2A.

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
