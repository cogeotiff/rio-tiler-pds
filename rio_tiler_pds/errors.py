"""Errors and warnings."""

from rio_tiler.errors import RioTilerError


class InvalidLandsatSceneId(RioTilerError):
    """Invalid Landsat-8 scene id."""


class InvalidSentinelSceneId(RioTilerError):
    """Invalid Sentinel-2 scene id."""


class InvalidCBERSSceneId(RioTilerError):
    """Invalid CBERS scene id."""


class InvalidMODISSceneId(RioTilerError):
    """Invalid MODIS scene id."""


class InvalidMODISProduct(RioTilerError):
    """Invalid MODIS Product."""
