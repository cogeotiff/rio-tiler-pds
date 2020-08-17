"""rio-tiler-pds.sentinel.aws"""

import re
from typing import Any, Union

from .sentinel1 import S1CReader  # noqa
from .sentinel2 import S2L1CReader, S2L2ACOGReader, S2L2AReader  # noqa

from ..utils import s2_sceneid_parser
from ...errors import InvalidSentinelSceneId


def SentinelReader(sceneid: str, *args: Any, **kwargs: Any) -> Union[S2L1CReader, S2L2ACOGReader, S2L2AReader, S1CReader]:
    """Select Reader based on Sceneid."""
    if sceneid.startswith("S1"):
        return S1CReader(sceneid, *args, **kwargs)

    if re.match("^S2[AB]_L[0-2][A-C]_[0-9]{8}_[0-9]{2}[A-Z]{3}_[0-9]$", sceneid):
        metadata = s2_sceneid_parser(sceneid)
        if metadata["processingLevel"] == "L1C":
            return S2L1CReader(sceneid, *args, **kwargs)
        elif metadata["processingLevel"] == "L2A":
            return S2L2AReader(sceneid, *args, **kwargs)

    if re.match("^S2[AB]_[0-9]{2}[A-Z]{3}_[0-9]{8}_[0-9]_L[0-2][A-C]$", sceneid):
        return S2L2ACOGReader(sceneid, *args, **kwargs)

    raise InvalidSentinelSceneId(f"Unrecognized Sceneid: {sceneid}")