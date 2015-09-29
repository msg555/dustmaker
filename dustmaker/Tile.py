from enum import IntEnum

class TileSpriteSet(IntEnum):
  """ Used to describe what set of tiles a tile's sprite comes from. """
  none = 0
  mansion = 1
  forest = 2
  city = 3
  laboratory = 4
  tutorial = 5

class TileSide(IntEnum):
  TOP = 0
  BOTTOM = 1
  LEFT = 2
  RIGHT = 3

class TileShape(IntEnum):
  """ Tiles come in four main types; full, half, big, and small.

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

tile_maximal_bits = [
  [ 15, 15, 15, 15, ], # TileShape.FULL: 
  [ 7, 15, 15, 0, ], # TileShape.BIG_1: 
  [ 11, 15, 0, 0, ], # TileShape.SMALL_1: 
  [ 15, 0, 15, 7, ], # TileShape.BIG_2: 
  [ 0, 0, 15, 11, ], # TileShape.SMALL_2:
  [ 15, 11, 0, 15, ], # TileShape.BIG_3: 
  [ 15, 7, 0, 0, ], # TileShape.SMALL_3: 
  [ 0, 15, 11, 15, ], # TileShape.BIG_4: 
  [ 0, 0, 7, 15, ], # TileShape.SMALL_4: 
  [ 11, 15, 0, 15, ], # TileShape.BIG_5: 
  [ 7, 15, 0, 0, ], # TileShape.SMALL_5: 
  [ 15, 0, 7, 15, ], # TileShape.BIG_6: 
  [ 0, 0, 11, 15, ], # TileShape.SMALL_6: 
  [ 15, 7, 15, 0, ], # TileShape.BIG_7: 
  [ 15, 11, 0, 0, ], # TileShape.SMALL_7:
  [ 0, 15, 15, 11, ], # TileShape.BIG_8: 
  [ 0, 0, 15, 7, ], # TileShape.SMALL_8: 
  [ 15, 15, 15, 0, ], # TileShape.HALF_A: 
  [ 15, 15, 15, 0, ], # TileShape.HALF_B: 
  [ 15, 15, 0, 15, ], # TileShape.HALF_C:
  [ 15, 15, 0, 15, ], # TileShape.HALF_D: 
]

class Tile:
  """ Represents a single tile in a Dustforce level.  Positional information
      is stored within Map.
  """
  """ Tile byte layout notes
        0x0 0,4 top
            1,5 bottom
            2,6 left
            3,7 right
        0x1 0..1 top
            2..3 bottom
            4..5 left
            6..7 right
        0x2 top angles
        0x3
        0x4 bottom angles
        0x5
        0x6 left angles
        0x7
        0x8 right angles
        0x9
        0xA 0..3 sprite set
            4..7 sprite palette
        0xB      sprite tile

        1 -> Mansion
        2 -> Forest
        3 -> City
        4 -> Lab
        5 -> Virtual
  """

  def __init__(self, shape, _tile_data = None, _dust_data = None):
    """ Initialize a vanilla virtual tile of the given shape. """
    self.shape = shape

    if _tile_data is None:
      self.tile_data = bytearray(12)
      for side in TileSide:
        self.edge_bits(side, tile_maximal_bits[shape][side])
        self.edge_angle(side, 0)
      self.sprite_set(TileSpriteSet.tutorial)
      self.sprite_tile(1)
      self.sprite_palette(0)
    else:
      self.tile_data = bytearray(_tile_data)

    if _dust_data is None:
      self.dust_data = None
    else:
      self.dust_data = bytearray(_dust_data)

  def edge_bits(self, side, val = None):
    """ Returns the 4 bit number associated with `side` surface of the tile.
        I'm unsure what each bit means currently.  Set all to 0 to freely move
        through that side of the tile and to 0xF to cause collisions.

        side -- The side to get/set edge bits.
        val -- If present a 4 bit integer to set as the new edge bits.
    """
    result = 0
    bits = [0 + side, 4 + side, 8 + 2 * side, 9 + 2 * side]
    for (i, bit) in enumerate(bits):
      if self.tile_data[bit >> 3] & (1 << (bit & 7)):
        result |= 1 << i
      if not val is None:
        self.tile_data[bit >> 3] &= ~(1 << (bit & 7))
        if val & 1 << i:
          self.tile_data[bit >> 3] |= 1 << (bit & 7)
    return result

  def edge_angle(self, side, val = None):
    """ Returns the angle of `side` as a 16 bit integer.

        side -- The side to get/set edge angle.
        val -- If present a 16 bit integer to set as the new edge angle.
    """
    result = (self.tile_data[2 + side * 2] +
              (self.tile_data[2 + side * 2 + 1] << 8))
    if not val is None:
      self.tile_data[2 + side * 2] = val & 0xFF
      self.tile_data[2 + side * 2 + 1] = val >> 8
    return result

  def sprite_set(self, val = None):
    """ Returns the sprite set from TileSpriteSet associated with this tile.

        val -- If present a TileSpriteSet to set as the new sprite set.
    """
    result = TileSpriteSet(self.tile_data[10] & 0xF)
    if not val is None:
      self.tile_data[10] = (self.tile_data[10] & 0xF0) | val
    return result

  def sprite_tile(self, val = None):
    """ Returns the tile index associated with this tile.

        val -- If present the new tile index for this tile.
    """
    result = self.tile_data[11]
    if not val is None:
      self.tile_data[11] = val
    return result

  def sprite_palette(self, val = None):
    """ Returns the palette index associated with this tile.

        val -- If present the new palette index for this tile.
    """
    result = (self.tile_data[10] & 0xF0) >> 4
    if not val is None:
      self.tile_data[10] = (self.tile_data[10] & 0x0F) | (val << 4)
    return result

  def sprite_path(self):
    """ Returns the palette index associated with this tile.  You may
        retrieve the complete game sprites listing from
        https://www.dropbox.com/s/jm37ew9p74olgca/sprites.zip?dl=0

        val -- If present the new palette index for this tile.
    """
    return "area/%s/tiles/tile%d_%d_0001.png" % (
        self.sprite_set().name, self.sprite_tile(), self.sprite_palette() + 1)
