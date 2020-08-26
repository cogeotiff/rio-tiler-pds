# Rio-Tiler-PDS: A rio-tiler plugin for Public Datasets

<p align="center">
  <img src="https://user-images.githubusercontent.com/10407788/91102350-ffa75400-e636-11ea-8374-3450a72745c9.png" style="max-width: 800px;" alt="rio-tiler-pds"></a>
</p>
<p align="center">
  <em>Rasterio plugin to access and read Public hosted datasets.</em>
</p>
<p align="center">
  <a href="https://github.com/cogeotiff/rio-tiler-pds/actions?query=workflow%3ACI" target="_blank">
      <img src="https://github.com/cogeotiff/rio-tiler-pds/workflows/CI/badge.svg" alt="Test">
  </a>
  <a href="https://codecov.io/gh/cogeotiff/rio-tiler-pds" target="_blank">
      <img src="https://codecov.io/gh/cogeotiff/rio-tiler-pds/branch/master/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/rio-tiler-pds" target="_blank">
      <img src="https://img.shields.io/pypi/v/rio-tiler-pds?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://pypistats.org/packages/rio-tiler-pds" target="_blank">
      <img src="https://img.shields.io/pypi/dm/rio-tiler-pds.svg" alt="Downloads">
  </a>
  <a href="https://github.com/cogeotiff/rio-tiler-pds/blob/master/LICENSE.txt" target="_blank">
      <img src="https://img.shields.io/github/license/cogeotiff/rio-tiler-pds.svg" alt="Lincense">
  </a>
</p>

**Important** This is the new module for rio-tiler missions specific (ref: https://github.com/cogeotiff/rio-tiler/issues/195)

## Install

You can install rio-tiler-pds using pip

```bash
$ pip install -U pip
$ pip install rio-tiler-pds
```

or install from source:

```bash
$ git clone https://github.com/cogeotiff/rio-tiler-pds.git
$ cd rio-tiler-pds
$ pip install -U pip
$ pip install -e .
```

## Datasets

Data | Level | Format | Owner | Bucket Type | Link
--- | --- | --- | --- | --- | ---
Sentinel 2 | L1C | JPEG2000 | Sinergise / AWS | **Requester-pays** | https://registry.opendata.aws/sentinel-2/
Sentinel 2 | L2A | JPEG2000 | Sinergise / AWS | **Requester-pays** | https://registry.opendata.aws/sentinel-2/
Sentinel 2 | L2A | COG | Digital Earth Africa / AWS | Public | https://www.digitalearthafrica.org/news/operational-and-ready-use-satellite-data-now-available-across-africa
Sentinel 1 | L1C | COG (Internal GCPS) | Sinergise / AWS | **Requester-pays** | https://registry.opendata.aws/sentinel-1/
Landsat 8  | L1 | GTiff (External Overviews) | Planet / AWS | Public | https://registry.opendata.aws/landsat-8/
CBERS 4 | L1 | COG | AMS Kepler / AWS | Public | https://registry.opendata.aws/cbers/

**Adding more dataset**:

If there is a dataset that can easily be described with a `scene id` please feel free to Open an Issue or a PR directly.

## Warnings

#### Requester-pays Buckets 

On AWS, `sentinel2`, `sentinel1`, and `cbers` dataset are stored in a `requester-pays` bucket, meaning the cost of GET, LIST requests will be charged to the users. For rio-tiler to work with those buckets, you'll need to set `AWS_REQUEST_PAYER="requester"` in your environement.

#### Partial reading on Cloud hosted dataset

Rio-tiler perform partial reading on local or distant dataset, which is why it will perform best on Cloud Optimized GeoTIFF (COG).
It's important to note that **Sentinel-2 scenes hosted on AWS are not in Cloud Optimized format but in JPEG2000**.
When performing partial reading of JPEG2000 dataset GDAL (rasterio backend library) will need to make a lot of **GET requests** and transfer a lot of data.

Ref: [Do you really want people using your data](https://medium.com/@_VincentS_/do-you-really-want-people-using-your-data-ec94cd94dc3f) blog post.

# Overview

## Readers

Each dataset has its own submodule (e.g sentinel2: `rio_tiler_pds.sentinel.aws`)

```python
from rio_tiler_pds.landsat.aws import L8Reader 
from rio_tiler_pds.sentinel.aws import S1L1CReader
from rio_tiler_pds.sentinel.aws import (
    S2L1CReader,  # JPEG2000
    S2L2AReader,  # JPEG2000
    S2L2ACOGReader,   # COG
)
from rio_tiler_pds.cbers.aws import CBERSReader
```

All Readers are subclass of [`rio_tiler.io.BaseReader`](https://github.com/cogeotiff/rio-tiler/blob/f917d0eaf27f8644f3bb18856a63fe45eeb4a2ef/rio_tiler/io/base.py#L17) and inherit its properties/methods.

#### Properties
- **bounds**: Scene bounding box
- **minzoom**: WebMercator MinZoom (e.g 7 for Landsat8)
- **maxzoom**: WebMercator MaxZoom (e.g 12 for Landsat8)
- **center**: Scene center
- **spatial_info**: zooms, bounds and center

#### Methods

- **info**: Returns asset's (band) simple info (e.g nodata, band_descriptions, ....)
- **stats**: Returns asset's statistics (percentile, histogram, ...)
- **metadata**: info + stats
- **tile**: Read web mercator map tile from assets (bands) 
- **part**: Extract part of assets (bands)
- **preview**: Returns a low resolution preview from assets (bands)
- **point**: Returns asset's pixel value for a given lon,lat

#### Other
- **assets**: List of available assets (bands) for each dataset

## Scene ID

All readers take scene id as main input. The **scene id** is used internaly by the reader to derive the full path of the data.

e.g: Landsat on AWS

Because the Landsat AWS PDS follows a regular schema to store the data (`s3://{bucket}/c1/L8/{path}/{row}/{scene}/{scene}_{asset}.TIF"`), we can easily reconstruct the full asset's path by parsing the scene id. 

```python
from rio_tiler_pds.landsat.aws import L8Reader 
from rio_tiler_pds.landsat.utils import sceneid_parser   

sceneid_parser("LC08_L1TP_016037_20170813_20170814_01_RT")
      
> {
  'sensor': 'C',
  'satellite': '08',
  'processingCorrectionLevel': 'L1TP',
  'path': '016',
  'row': '037',
  'acquisitionYear': '2017',
  'acquisitionMonth': '08',
  'acquisitionDay': '13',
  'processingYear': '2017',
  'processingMonth': '08',
  'processingDay': '14',
  'collectionNumber': '01',
  'collectionCategory': 'RT',
  'scene': 'LC08_L1TP_016037_20170813_20170814_01_RT',
  'date': '2017-08-13'
}

with L8Reader("LC08_L1TP_016037_20170813_20170814_01_RT") as landsat: 
    print(landsat._get_asset_url("B1")) 
            
> s3://landsat-pds/c1/L8/016/037/LC08_L1TP_016037_20170813_20170814_01_RT/LC08_L1TP_016037_20170813_20170814_01_RT_B1.TIF
```

Each Dataset have their specific scene id format:

<details>

- Landsat
  - link: [rio_tiler_pds.landsat.utils.sceneid_parser](https://github.com/cogeotiff/rio-tiler-pds/blob/e4421d3cf7c23b7b3552b8bb16ee5913a5483caf/rio_tiler_pds/landsat/utils.py#L35-L56)
  - regex: `^L[COTEM]0[0-9]_L\d{1}[A-Z]{2}_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2|RT)$` 
  - example: `LC08_L1TP_016037_20170813_20170814_01_RT`

- Sentinel 1 L1C
  - link: [rio_tiler_pds.sentinel.utils.s1_sceneid_parser](https://github.com/cogeotiff/rio-tiler-pds/blob/e4421d3cf7c23b7b3552b8bb16ee5913a5483caf/rio_tiler_pds/sentinel/utils.py#L98-L121)
  - regex: `^S1[AB]_(IW)|(EW)_[A-Z]{3}[FHM]_[0-9][SA][A-Z]{2}_[0-9]{8}T[0-9]{6}_[0-9]{8}T[0-9]{6}_[0-9A-Z]{6}_[0-9A-Z]{6}_[0-9A-Z]{4}$`
  - example: `S1A_IW_GRDH_1SDV_20180716T004042_20180716T004107_022812_02792A_FD5B`

- Sentinel 2 JPEG200 and Sentinel 2 COG 
  - link: [rio_tiler_pds.sentinel.utils.s2_sceneid_parser](https://github.com/cogeotiff/rio-tiler-pds/blob/e4421d3cf7c23b7b3552b8bb16ee5913a5483caf/rio_tiler_pds/sentinel/utils.py#L25-L60)
  - regex: `^S2[AB]_[0-9]{2}[A-Z]{3}_[0-9]{8}_[0-9]_L[0-2][A-C]$` or `^S2[AB]_L[0-2][A-C]_[0-9]{8}_[0-9]{2}[A-Z]{3}_[0-9]$`
  - example: `S2A_29RKH_20200219_0_L2A`, `S2A_L1C_20170729_19UDP_0`, `S2A_L2A_20170729_19UDP_0`

- CBERS
  - link: [rio_tiler_pds.cbers.utils.sceneid_parser](https://github.com/cogeotiff/rio-tiler-pds/blob/e4421d3cf7c23b7b3552b8bb16ee5913a5483caf/rio_tiler_pds/cbers/utils.py#L26-L41)
  - regex: `^CBERS_4_\w+_[0-9]{8}_[0-9]{3}_[0-9]{3}_L[0-9]$`
  - example: `CBERS_4_MUX_20171121_057_094_L2`, `CBERS_4_AWFI_20170420_146_129_L2`, `CBERS_4_PAN10M_20170427_161_109_L4`, `CBERS_4_PAN5M_20170425_153_114_L4`

</details>

## File Per Band

rio-tiler-pds Readers assume that assets (eo:band) are stored in separate files. 

```bash
$ aws s3 ls landsat-pds/c1/L8/013/031/LC08_L1TP_013031_20130930_20170308_01_T1/

LC08_L1TP_013031_20130930_20170308_01_T1_B1.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B10.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B11.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B2.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B3.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B4.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B5.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B6.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B7.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B8.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_B9.TIF
LC08_L1TP_013031_20130930_20170308_01_T1_BQA.TIF
```

When reading data or metadata, readers will merge them.

e.g 
```python
with S2L1CReader("S2A_L1C_20170729_19UDP_0") as sentinel:
    tile, mask = sentinel.tile(77, 89, 8, assets=("B01", "B02")
    assert tile.shape == (2, 256, 256)

    print(sentinel.stats(assets=("B8A", "B02")))
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
      },
      'B02': {
        ...
      }
    }
```

## Usage

### Sentinel 2 - AWS

#### L1C - JPEG2000

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

#### L2A - JPEG2000

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

#### L2A - COG

assets: `B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A`

Note: `AOT, SCL, WVP` assets are not supported.

```python
from rio_tiler_pds.sentinel.aws import S2L2ACOGReader  

with S2L2ACOGReader("S2A_29RKH_20200219_0_L2A") as sentinel: 
    print(sentinel.assets)
    > ('B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A')

    # bounds and metadata are derived from the STAC item stored with the COG
    print(type(sentinel.stac_item))
    > dict
```

### Sentinel 1 - AWS

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

### Landsat 8 - AWS

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

### CBERS 4 - AWS

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

## Contribution & Development

See [CONTRIBUTING.md](https://github.com/cogeotiff/rio-tiler/blob/master/CONTRIBUTING.md)

## License

See [LICENSE.txt](https://github.com/cogeotiff/rio-tiler-pds/blob/master/LICENSE.txt)

## Authors

The rio-tiler project was begun at Mapbox and has been transferred in January 2019.

See [AUTHORS.txt](https://github.com/cogeotiff/rio-tiler-pds/blob/master/AUTHORS.txt) for a listing of individual contributors.

## Changes

See [CHANGES.txt](https://github.com/cogeotiff/rio-tiler-pds/blob/master/CHANGES.txt).

