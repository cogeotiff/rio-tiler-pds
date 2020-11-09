"""AWS Sentinel 1 & 2 readers"""

from .sentinel1 import S1L1CReader  # noqa
from .sentinel2 import (  # noqa
    S2COGReader,
    S2JP2Reader,
    S2L1CReader,
    S2L2ACOGReader,
    S2L2AReader,
)
