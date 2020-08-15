"""Errors and warnings."""

from rio_tiler.errors import RioTilerError


class InvalidLandsatSceneId(RioTilerError):
    """Invalid Landsat-8 scene id."""


class InvalidSentinelSceneId(RioTilerError):
    """Invalid Sentinel-2 scene id."""


class InvalidCBERSSceneId(RioTilerError):
    """Invalid CBERS scene id."""


class MissingBands(RioTilerError):
    """Missing bands."""
