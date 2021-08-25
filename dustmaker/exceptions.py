""" Module defining shared exception classes. """


class LevelException(Exception):
    """Top level dustmaker exception."""


class LevelParseException(LevelException):
    """Exception indicating an error reading a level file."""
