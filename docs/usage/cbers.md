## CBERS 4 - AWS

```python
from rio_tiler_pds.cbers.aws import CBERSReader

CBERS_MUX_SCENE = "CBERS_4_MUX_20171121_057_094_L2"
CBERS_AWFI_SCENE = "CBERS_4_AWFI_20170420_146_129_L2"
CBERS_PAN10M_SCENE = "CBERS_4_PAN10M_20170427_161_109_L4"
CBERS_PAN5M_SCENE = "CBERS_4_PAN5M_20170425_153_114_L4"


with CBERSReader("CBERS_4_MUX_20171121_057_094_L2") as cbers:
    print(cbers.bands)
    >>> ('B5', 'B6', 'B7', 'B8')

    print(cbers.bounds)
    >>> (53.302020833057796, 4.756472757234311, 54.628483877373, 6.025171883475984)

    assert cbers.minzoom == 8
    assert cbers.maxzoom == 12

with CBERSReader("CBERS_4_AWFI_20170420_146_129_L2") as cbers:
    print(cbers.bands)
    >>> ('B13', 'B14', 'B15', 'B16')

with CBERSReader("CBERS_4_PAN10M_20170427_161_109_L4") as cbers:
    print(cbers.bands)
    >>> ('B2', 'B3', 'B4')


with CBERSReader("CBERS_4_PAN5M_20170425_153_114_L4") as cbers:
    print(cbers.bands)
    >>> ('B1',)
```
