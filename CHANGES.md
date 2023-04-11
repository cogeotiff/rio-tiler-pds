# Release Notes

## 0.8.0 (2023-04-11)

* remove Landsat 8 Collection 1
* remove python 3.7 and add python 3.10/3.11 support
* switch to ruff
* fix issue with latest STAC Items for Sentinel-2-l2a-cogs (author @dvd3v, https://github.com/cogeotiff/rio-tiler-pds/pull/64)
* update rio-tiler requirement to `>=4.0,<5.0`

## 0.7.0 (2022-06-08)

* enable `bucket` and `prefix_pattern` as input (@author @f-skold, https://github.com/cogeotiff/rio-tiler-pds/pull/61)
* switch to `pyproject.toml`

## 0.6.0 (2021-11-29)

* update rio-tiler requirement to `>=3.0.0`

**breaking changes**

* remove python 3.6 support
* `sceneid` -> `input` in Reader attributes
* remove `.stats()` and `.metadata()` methods
* `bands` is now optional for `.info()` and `.statistics`
* remove useless `band_expression` option

## 0.5.4 (2021-10-08)

* `bands` should be stored as `tuple` in sentinel-1 reader

## 0.5.3 (2021-10-08)

* Fix invalid sceneid parser for Sentinel-1

## 0.5.2 (2021-10-06)

* Fix available `bands` for Sentinel-1 based on Polarisation type (https://github.com/cogeotiff/rio-tiler-pds/pull/59)

## 0.5.1 (2021-06-25)

* fix landsat `sceneid_parser` for Collection 2 Albers dataset (https://github.com/cogeotiff/rio-tiler-pds/pull/56)
* allow `standard` and `albers` collections for Landsat Collection 2 reader (https://github.com/cogeotiff/rio-tiler-pds/pull/58)

## 0.5.0 (2021-02-02)

* add AWS's Landsat Collection 2 support (author @kylebarron, https://github.com/cogeotiff/rio-tiler-pds/pull/42)
* add sentinel-2 product ID parsing (ref: https://github.com/cogeotiff/rio-tiler-pds/pull/33).
* fix issue where the sequence number of a sentinel scene id can be two digit (ref: https://github.com/cogeotiff/rio-tiler-pds/pull/35)
* fix issue where `utm` is only one sigle digit (ref: https://github.com/cogeotiff/rio-tiler-pds/pull/34)
* add top level export (https://github.com/cogeotiff/rio-tiler-pds/issues/45)
* removes `get_object` from top level export
* add deprecation warning in L8Reader (https://github.com/cogeotiff/rio-tiler-pds/issues/40)

## 0.4.1 (2020-11-24)

* update for rio-tiler 2.0.0rc3

## 0.4.0 (2020-11-09)

* update for rio-tiler==2.0.0rc
* internal refactor of the Landsat8 reader
* add `sentinel.aws.sentinel2.S2JP2Reader` and `aws.sentinel2.S2COGReader` proxies to readers.

```python
from rio_tiler_pds.sentinel.aws import S2COGReader, S2JP2Reader

with S2JP2Reader("S2A_L2A_20170729_19UDP_0") as scene:
    print(type(scene))
>>> <class 'rio_tiler_pds.sentinel.aws.sentinel2.S2L2AReader'>

with S2JP2Reader("S2A_L1C_20170729_19UDP_0") as scene:
    print(type(scene))
>>> <class 'rio_tiler_pds.sentinel.aws.sentinel2.S2L1CReader'>


with S2COGReader("S2A_29RKH_20200219_0_L2A") as scene:
    print(type(scene))
>>> <class 'rio_tiler_pds.sentinel.aws.sentinel2.S2L2ACOGReader'>
```

## 0.3.2 (2020-10-13)

* add `TMS` options to adapt  for rio-tiler 2.0.0b17 (ref: https://github.com/cogeotiff/rio-tiler/pull/285)

## 0.3.1 (2020-10-07)

* remove `pkg_resources` (https://github.com/pypa/setuptools/issues/510)

## 0.3.0 (2020-10-03)

* Update sentinel2-cogs image path (https://github.com/cogeotiff/rio-tiler-pds/pull/22).
* Remove ContextManager requirement in base class and update for rio-tiler 2.0b13 (https://github.com/cogeotiff/rio-tiler/pull/265).
* Add MODIS (PDS and Astraea) dataset (https://github.com/cogeotiff/rio-tiler-pds/issues/18)
* move reader base classes to rio-tiler (https://github.com/cogeotiff/rio-tiler-pds/issues/24)
* add missing `0` (e.g "B1" -> "B01") when user forget it on sentinel and modis band names (https://github.com/cogeotiff/rio-tiler-pds/issues/25)


## 0.2.1 (2020-09-25)

* add support for CBERS-4A (author @fredliporace)

## 0.2.0 (2020-08-31)
* Revert the use of `assets` options to `bands` (#12)

```python
from rio_tiler_pds.landsat.aws import L8Reader

with L8Reader("LC08_L1TP_016037_20170813_20170814_01_RT") as landsat:
    # in 0.1.1 (PAST)
    tile, data = landsat.tile(x, y, z, assets="B1")

    # in 0.2.0 (NOW)
    tile, data = landsat.tile(x, y, z, bands="B1")
```


## 0.1.1 (2020-08-28)

* avoid `nodata` options colision with kwargs in L8Reader

## 0.1.0 (2020-08-27)

Initial release.

* Move code from rio-tiler
* Update for rio-tiler==2.0b8 (use COGReader and MultiBaseReader)
* Create new Classes (using attrs) and use ContextManager (`with Reader("sceneid") as scene:`)
* Remove Landsat 8 pre-collection support
* Add Sentinel 2 COGs dataset support
* Use TileInfo.json and ProductInfo.json to retrieve Sentinel 1 & 2 bounds
* Use `assets` options instead of `bands`
* Add `expression` options in readers

#### Readers
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

#### Example
```python
from rio_tiler_pds.landsat.aws import L8Reader

with L8Reader("LC08_L1TP_016037_20170813_20170814_01_RT") as landsat:
    tile, data = landsat.tile(x, y, z, assets="B1")
    tile, data = landsat.tile(x, y, z, expression="B1/B2")
```
