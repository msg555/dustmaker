"""
Commonly used enums in Dustmaker
"""
from enum import IntEnum


class LevelType(IntEnum):
    """
    Enum defining the different level types
    """

    NORMAL = 0
    NEXUS = 1
    NEXUS_MP = 2
    KOTH = 3
    SURVIVAL = 4
    DUSTMOD = 6


class CameraNodeType(IntEnum):
    """
    Enum defining the different camera node types
    """

    NORMAL = 1
    DETACH = 2
    CONNECT = 3
    INTEREST = 4
    FORCE_CONNECT = 5


class TileSpriteSet(IntEnum):
    """Used to describe what set of tiles a tile's sprite comes from."""

    NONE_0 = 0
    MANSION = 1
    FOREST = 2
    CITY = 3
    LABORATORY = 4
    TUTORIAL = 5
    NEXUS = 6
    NONE_7 = 7


class TileSide(IntEnum):
    """Used to index the sides of a tile."""

    TOP = 0
    BOTTOM = 1
    LEFT = 2
    RIGHT = 3


class TileShape(IntEnum):
    """Tiles come in four main types; full, half, big, and small.

    Full corresponds to a complete square tile.

    Half corresponds to one of the tiles aligned to 45 degrees that take up
    half of the tile unit.  These come in four varieties A, B, C, and D
    depicted on the wheel below.

    Big and small tiles form the inbetween angles.  The big tile variant
    covers 75% of the tile while the small tile variant covers 25% of the
    tile.  Each of these comes in 8 varieties 1-8 depicted in the wheel below.

    To determine the angle of a half, big, or small tile from its shape find
    its identifier in the wheel.  Imagine you were located at X and the +
    characters formed a circle around you; the angle of the tile would be
    approximately the angle of the circle surface where its label is.::

              +++++
           +7+     +3+
          +           +
         +             +
        B               C
       +                 +
      +                   +
      2                   6
      +                   +
     +                     +
     +                     +
     +          X          +
     +                     +
     +                     +
      +                   +
      8                   4
      +                   +
       +                 +
        A               D
         +             +
          +           +
           +1+     +5+
              +++++
    """

    FULL = 0
    BIG_1 = 1
    SMALL_1 = 2
    BIG_2 = 3
    SMALL_2 = 4
    BIG_3 = 5
    SMALL_3 = 6
    BIG_4 = 7
    SMALL_4 = 8
    BIG_5 = 9
    SMALL_5 = 10
    BIG_6 = 11
    SMALL_6 = 12
    BIG_7 = 13
    SMALL_7 = 14
    BIG_8 = 15
    SMALL_8 = 16
    HALF_A = 17
    HALF_B = 18
    HALF_C = 19
    HALF_D = 20
