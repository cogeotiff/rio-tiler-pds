## CBERS 4 - AWS

Since data are requester pays, we need to set an environment variable to access the data through `rasterio`.

```bash
AWS_REQUEST_PAYER="requester"
```

You can either set those variables in your environment or within your code using `rasterio.Env()`.

```python
import rasterio
from rio_tiler_pds.cbers.aws import CBERSReader

CBERS_MUX_SCENE = "CBERS_4_MUX_20171121_057_094_L2"
CBERS_AWFI_SCENE = "CBERS_4_AWFI_20170420_146_129_L2"
CBERS_PAN10M_SCENE = "CBERS_4_PAN10M_20170427_161_109_L4"
CBERS_PAN5M_SCENE = "CBERS_4_PAN5M_20170425_153_114_L4"

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with CBERSReader("CBERS_4_MUX_20171121_057_094_L2") as cbers:
        print(cbers.bands)
        >>> ('B5', 'B6', 'B7', 'B8')

        print(cbers.bounds)
        >>> (90480.0, 526840.0, 236940.0, 666560.0)

        print(cbers.geographic_bounds)
        >>> (53.3020208330578, 4.756472757234312, 54.628483877373014, 6.025171883475984)

        assert cbers.minzoom == 8
        assert cbers.maxzoom == 12

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with CBERSReader("CBERS_4_AWFI_20170420_146_129_L2") as cbers:
        print(cbers.bands)
        >>> ('B13', 'B14', 'B15', 'B16')

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with CBERSReader("CBERS_4_PAN10M_20170427_161_109_L4") as cbers:
        print(cbers.bands)
        >>> ('B2', 'B3', 'B4')

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with CBERSReader("CBERS_4_PAN5M_20170425_153_114_L4") as cbers:
        print(cbers.bands)
        >>> ('B1',)
```
