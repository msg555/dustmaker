"""
Module defining shared exception classes.
"""


class MapException(Exception):
    """Top level dustmaker exception."""


class MapParseException(MapException):
    """Exception indicating an error reading a map file."""
