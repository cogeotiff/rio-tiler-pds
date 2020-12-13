# Usage

## Requester-Pays

Some data are stored on AWS requester-pays buckets (you are charged for LIST/GET requests and data transfer outside the bucket region). For those datasets you need to set `AWS_REQUEST_PAYER="requester"` environement variable to tell AWS S3 that you agree with requester-pays principle.

You can either set those variables in your environment or within your code using `rasterio.Env()`.

```python
import rasterio
from rio_tiler_pds.sentinel.aws import S2JP2Reader

with rasterio.Env(AWS_REQUEST_PAYER="requester"):
    with S2JP2Reader("S2A_L1C_20170729_19UDP_0") as s2:
        print(s2.preview(bands="B01", width=64, height=64))
```
