"""
Commonly used enums in Dustmaker
"""
from enum import IntEnum


class CameraNodeType(IntEnum):
    """
    Enum defining the different camera node types
    """

    NORMAL = 1
    DETACH = 2
    CONNECT = 3
    INTEREST = 4
    FORCE_CONNECT = 5
