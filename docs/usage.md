
# Usage

## Sentinel 2 - AWS

### L1C - JPEG2000

assets: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

```python
from rio_tiler_pds.sentinel.aws import S2L1CReader

# We use __enter__ context manager for the Reader.
# When creating the instance of `sentinel` the Reader will fetch the sentinel 2 TileInfo.json
# to retrieve the bounds of the dataset and other metadata available at `sentinel.tileInfo`.
with S2L1CReader("S2A_L1C_20170729_19UDP_0") as sentinel:
    # bounds and metadata are derived from the tileInfo.json file stored with the JPEG2000
    print(type(sentinel.tileInfo))
    > dict

    print(type(sentinel.datageom))
    > dict

    print(sentinel.center)
    > (-69.4190338105916, 48.25699850457617, 8)

    print(sentinel.info(assets="B01"))
    > {
        'bounds': (-69.97083660271242, 47.761069480166974, -68.86723101847078, 48.75292752898536),
        'center': (-69.4190338105916, 48.25699850457617, 8),
        'minzoom': 8,
        'maxzoom': 14,
        'band_metadata': [(1, {})],
        'band_descriptions': [(1, 'B01')],
        'dtype': 'uint16',
        'colorinterp': ['gray'],
        'nodata_type': 'None'
      }

    print(sentinel.stats(assets="B8A"))
    > {
      'B8A': {
        'pc': [106, 9322],
        'min': 1,
        'max': 13659,
        'std': 2682.6511198930048,
        'histogram': [
          [261631, 52188, 137746, 98039, 41066, 30818, 21095, 8631, 1442, 105],
          [1.0, 1366.8, 2732.6, 4098.4, 5464.2, 6830.0, 8195.8, 9561.6, 10927.4, 12293.199999999999, 13659.0]
        ]
      }
    }

    tile, mask = sentinel.tile(77, 89, 8, assets="B01")
    assert tile.shape == (1, 256, 256)

    print(sentinel.point(-69.41, 48.25, assets=("B01", "B02")))
    # Result is in form of 
    # [
    #   value for band 1 in asset B01,
    #   value for band 1 in asset B02
    # ]
    > [1230, 875]

    # Working with Expression
    tile, mask = sentinel.tile(77, 89, 8, expression="B01/B02")
    assert tile.shape == (1, 256, 256)

    print(sentinel.point(-69.41, 48.25, expression="B01/B02"))
    > [1.424673784104389]
```

### L2A - JPEG2000

assets: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

Note: `AOT, SCL, WVP` assets are not supported.

```python
from rio_tiler_pds.sentinel.aws import S2L2AReader

with S2L2AReader("S2A_L2A_20170729_19UDP_0") as sentinel:
    # bounds and metadata are derived from the tileInfo.json file stored with the JPEG2000
    print(type(sentinel.tileInfo))
    > dict

    print(type(sentinel.datageom))
    > dict

    print(sentinel.info(assets="B01"))
    > {
        'bounds': (-69.96945818759949, 47.7610811323474, -68.86723101847078, 48.75292752898536),
        'center': (-69.41834460303514, 48.257004330666376, 8),
        'minzoom': 8,
        'maxzoom': 14,
        'band_metadata': [(1, {})],
        'band_descriptions': [(1, 'B01')],
        'dtype': 'uint16',
        'colorinterp': ['gray'],
        'nodata_type': 'None'
      }
```

### COG (Only L2A available for now)

assets: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

Note: `AOT, SCL, WVP` assets are not supported.

```python
from rio_tiler_pds.sentinel.aws import S2COGReader  

with S2COGReader("S2A_29RKH_20200219_0_L2A") as sentinel: 
    print(sentinel.assets)
    > ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A')

    # bounds and metadata are derived from the STAC item stored with the COG
    print(type(sentinel.stac_item))
    > dict
```

## Sentinel 1 - AWS

```python
from rio_tiler_pds.sentinel.aws import S1L1CReader

with S1L1CReader("S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B") as sentinel:
    print(sentinel.assets)
    > ('vv', 'vh')

    print(sentine.bounds)
    > (75.605247, 9.225784, 78.203903, 11.190425)

    print(type(sentinel.productInfo))
    > dict

    print(sentinel._get_asset_url("vv"))
    > 's3://sentinel-s1-l1c/GRD/2018/7/16/IW/DV/S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B/measurement/iw-vv.tiff'
```

## Landsat 8 - AWS

```python
from rio_tiler_pds.landsat.aws import L8Reader

with L8Reader("LC08_L1TP_016037_20170813_20170814_01_RT") as landsat:
    print(landsat.assets)
    > ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'BQA'
    assert landsat.minzoom == 7
    assert landsat.minzoom == 12

    print(landsat.spatial_info)
    > {
      'bounds': (-81.30836, 32.10539, -78.82045, 34.22818),
      'center': (-80.064405, 33.166785000000004, 7),
      'minzoom': 7,
      'maxzoom': 12
    }
    
    print(landsat.info(assets="B1"))
    > {
      'bounds': (-81.30836, 32.10539, -78.82045, 34.22818),
      'center': (-80.064405, 33.166785000000004, 7),
      'minzoom': 7,
      'maxzoom': 12,
      'band_metadata': [(1, {})],
      'band_descriptions': [(1, 'B1')],
      'dtype': 'uint16',
      'colorinterp': ['gray'],
      'nodata_type': 'None'
    }

    print(landsat.stats(assets="B1"))
    > {
      'B1': {
        'pc': [1207, 6989],
        'min': 922,
        'max': 13512,
        'std': 297,
        'histogram': [
          [574527, 54320, 37316, 25318, 15086, 8101, 3145, 744, 160, 21],
          [922, 2181, 3440, 4699, 5958, 7217, 8476, 9735, 10994, 12253, 13512]
        ]
      }
    }

    tile_z = 8
    tile_x = 71
    tile_y = 102
    tile, mask = landsat.tile(tile_x, tile_y, tile_z, assets=("B4", "B3", "B2"))
    assert tile.shape == (3, 256, 256)

    data, mask = landsat.tile(tile_x, tile_y, tile_z, assets="B10")
    assert data.shape == (1, 256, 256)

    tile, mask = landsat.tile(
        tile_x, tile_y, tile_z, assets=("B4", "B3", "B2"), pan=True
    )
    assert tile.shape == (3, 256, 256)

    tile, mask = landsat.tile(
        tile_x, tile_y, tile_z, expression="B5*0.8, B4*1.1, B3*0.8"
    )
    assert tile.shape == (3, 256, 256)

    data, mask = landsat.preview(
        assets=("B4", "B3", "B2"), pan=True, width=256, height=256
    )
    assert data.shape == (3, 256, 256)
```

## CBERS 4 - AWS

```python
from rio_tiler_pds.cbers.aws import CBERSReader

CBERS_MUX_SCENE = "CBERS_4_MUX_20171121_057_094_L2"
CBERS_AWFI_SCENE = "CBERS_4_AWFI_20170420_146_129_L2"
CBERS_PAN10M_SCENE = "CBERS_4_PAN10M_20170427_161_109_L4"
CBERS_PAN5M_SCENE = "CBERS_4_PAN5M_20170425_153_114_L4"


with CBERSReader("CBERS_4_MUX_20171121_057_094_L2") as cbers:
    print(cbers.assets)
    > ('B5', 'B6', 'B7', 'B8')

    print(cbers.bounds)
    > (53.302020833057796, 4.756472757234311, 54.628483877373, 6.025171883475984)

    assert cbers.minzoom == 8
    assert cbers.maxzoom == 12

with CBERSReader("CBERS_4_AWFI_20170420_146_129_L2") as cbers:
    print(cbers.assets)
    > ('B13', 'B14', 'B15', 'B16')

with CBERSReader("CBERS_4_PAN10M_20170427_161_109_L4") as cbers:
    print(cbers.assets)
    > ('B2', 'B3', 'B4')


with CBERSReader("CBERS_4_PAN5M_20170425_153_114_L4") as cbers:
    print(cbers.assets)
    > ('B1',)
```
