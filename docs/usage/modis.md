## MODIS - AWS

### PDS (modis-pds bucket)

**Products**: MCD43A4, MOD09GQ, MYD09GQ, MOD09GA, MYD09GA

```python
from rio_tiler_pds.modis.aws import MODISPDSReader

MCD43A4_SCENE = "MCD43A4.A2017006.h21v11.006.2017018074804"
with MODISPDSReader(MCD43A4_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B01qa", "B02", "B02qa", "B03", "B03qa", "B04", "B04qa", "B05", "B05qa", "B06", "B06qa", "B07", "B07qa")

    print(modis.bounds)
    >>> (31.9253, -30.0, 46.1976, -20.0)

    assert modis.minzoom == 4
    assert modis.maxzoom == 9

MOD09GA_SCENE = "MOD09GA.A2017129.h34v07.006.2017137214839"
with MODISPDSReader(MOD09GA_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "geoflags", "granule", "numobs1km", "numobs500m", "obscov", "obsnum", "orbit", "qc500m", "qscan", "range", "senaz", "senzen", "solaz", "solzen", "state")

MOD09GQ_SCENE = "MOD09GQ.A2017120.h29v09.006.2017122031126"
with MODISPDSReader(MOD09GQ_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B02", "granule", "numobs", "obscov", "obsnum", "orbit", "qc")
```

### ASTRAEA (astraea-opendata bucket)

**Products**: MCD43A4, MOD11A1, MOD13A1, MYD11A1 MYD13A1

```python
from rio_tiler_pds.modis.aws import MODISASTRAEAReader

MCD43A4_SCENE = "MCD43A4.A2017006.h21v11.006.2017018074804"
with MODISASTRAEAReader(MCD43A4_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B01qa", "B02", "B02qa", "B03", "B03qa", "B04", "B04qa", "B05", "B05qa", "B06", "B06qa", "B07", "B07qa")

    print(modis.bounds)
    >>> (31.9253, -30.0, 46.1976, -20.0)

    assert modis.minzoom == 4
    assert modis.maxzoom == 9

MOD11A1_SCENE = "MOD11A1.A2020250.h20v11.006.2020251085003"
with MODISASTRAEAReader(MOD11A1_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12")

MOD13A1_SCENE = "MOD13A1.A2020049.h14v04.006.2020066002045"
with MODISASTRAEAReader(MOD13A1_SCENE) as modis:
    print(modis.bands)
    >>> ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12")
```
