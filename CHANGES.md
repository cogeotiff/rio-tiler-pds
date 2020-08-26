# Release Notes

## 0.0.1 (2020-08-25)

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

with L8Reader("LC08_L1TP_016037_20170813_20170814_01_RT") as landsat: 
    tile, data = landsat.tile(x, y, z, assets="B1")
    tile, data = landsat.tile(x, y, z, expression="B1/B2")
```
