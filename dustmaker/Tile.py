from enum import IntEnum

import math
import copy

class TileSpriteSet(IntEnum):
  """ Used to describe what set of tiles a tile's sprite comes from. """
  none_0 = 0
  mansion = 1
  forest = 2
  city = 3
  laboratory = 4
  tutorial = 5
  nexus = 6
  none_7 = 7

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

# Full - Clockwise from top
# Small/Big/Half - Clockwise from hyp. (ccw from mirrored)
shape_ordered_sides = [
  [0, 2, 1, 3],
  [0, 1, 2],
  [0, 1],
  [3, 2, 0],
  [3, 2],
  [1, 0, 3],
  [1, 0],
  [2, 3, 1],
  [2, 3],
  [0, 1, 3],
  [0, 1],
  [2, 3, 0],
  [2, 3],
  [1, 0, 2],
  [1, 0],
  [3, 2, 1],
  [3, 2],
  [0, 1, 2],
  [1, 2, 0],
  [1, 0, 3],
  [0, 3, 1],
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
      self.dust_data = bytearray(12)
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


  def has_filth(self):
    return self.dust_data[0] != 0 or self.dust_data[1] != 0

  def edge_filth_sprite(self, side, sprite_set = None, spikes = None):
    ind = side // 2
    shft = 4 * (side % 2)
    result = (self.dust_data[ind] >> shft) & 0xF
    if not sprite_set is None and not spikes is None:
      val = sprite_set | (0x8 if spikes else 0x0)
      self.dust_data[ind] &= 0xF0 >> shft
      self.dust_data[ind] |= val << shft
    return (TileSpriteSet(result & 0x7), (result & 0x8) != 0)

  def edge_filth_angles(self, side, angle1 = None, angle2 = None):
    ind = 2 + side * 2
    ang1 = int(self.dust_data[ind])
    ang2 = int(self.dust_data[ind + 1])
    if not angle1 is None:
      self.dust_data[ind] = angle1
    if not angle2 is None:
      self.dust_data[ind + 1] = angle2
    return (ang1, ang2)

  def edge_filth_cap(self, side, val = None):
    shft = 2 * side
    result = (self.dust_data[10] >> shft) & 0x3
    if not val is None:
      self.dust_data[10] &= ~(0x3 << shft)
      self.dust_data[10] |= val << shft
    return result

  def is_dustblock(self):
    dustblocks = {
      TileSpriteSet.mansion: 21,
      TileSpriteSet.forest: 13,
      TileSpriteSet.city: 6,
      TileSpriteSet.laboratory: 9,
      TileSpriteSet.tutorial: 2,
    }
    st = self.sprite_set()
    tl = self.sprite_tile()
    return dustblocks.get(st, -1) == tl

  def transform(self, mat):
    global shape_ordered_sides

    oshape = self.shape
    flipped = mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0] < 0
    if flipped:
      if self.shape == TileShape.FULL:
        pass
      elif self.shape <= TileShape.SMALL_8:
        self.shape = 1 + ((self.shape - TileShape.BIG_1) ^ 8) % 16
      else:
        self.shape = 17 + ((self.shape - TileShape.HALF_A) ^ 3)
    angle = int(round(math.atan2(mat[1][1], mat[1][0]) / math.pi * 2))
    angle = (-angle + 1) & 0x3

    if self.shape == TileShape.FULL:
      pass
    elif self.shape <= TileShape.SMALL_4:
      self.shape = 1 + ((self.shape - TileShape.BIG_1) + angle * 2) % 8
    elif self.shape <= TileShape.SMALL_8:
      self.shape = 9 + ((self.shape - TileShape.BIG_5) - angle * 2) % 8
    else:
      self.shape = 17 + ((self.shape - TileShape.HALF_A) + angle) % 4

    nbits = []
    nfilth_sprite = []
    nfilth_cap = []
    nangle = []
    for side in shape_ordered_sides[oshape]:
      nbits.append(self.edge_bits(side))
      nfilth_sprite.append(self.edge_filth_sprite(side))
      nfilth_cap.append(self.edge_filth_cap(side))
      nangle.append(self.edge_angle(side))
    for side in TileSide:
      self.edge_bits(side, 0)
      self.edge_filth_sprite(side, TileSpriteSet.none_0, False)
      self.edge_filth_cap(side, 0)
      self.edge_angle(side, 0)
    for (i, side) in enumerate(shape_ordered_sides[self.shape]):
      if self.shape == TileShape.FULL:
        i = i + angle & 3
        if flipped:
          i = -i & 3
      self.edge_bits(side, nbits[i])
      self.edge_filth_sprite(side, *nfilth_sprite[i])
      self.edge_filth_cap(side, nfilth_cap[i])
      self.edge_angle(side, nangle[i])

  def _copy_sides(self, tile, sides):
    for side in sides:
      self.edge_bits(side, tile.edge_bits(side))
      self.edge_filth_sprite(side, *tile.edge_filth_sprite(side))
      self.edge_filth_cap(side, tile.edge_filth_cap(side))

  def upscale(self, factor):
    result = []

    base_tile = Tile(TileShape.FULL)
    base_tile.sprite_set(self.sprite_set())
    base_tile.sprite_tile(self.sprite_tile())
    base_tile.sprite_palette(self.sprite_palette())
    for side in TileSide:
      base_tile.edge_bits(side, 0x0)

    if self.shape == TileShape.FULL:
      for dx in range(factor):
        for dy in range(factor):
          sides = []
          if dx == 0: sides.append(TileSide.LEFT)
          if dx + 1 == factor: sides.append(TileSide.RIGHT)
          if dy == 0: sides.append(TileSide.TOP)
          if dy + 1 == factor: sides.append(TileSide.BOTTOM)
          tile = copy.deepcopy(base_tile)
          tile._copy_sides(self, sides)
          result.append((dx, dy, tile))

    elif self.shape == TileShape.BIG_1:
      for dx in range(factor):
        for dy in range(dx // 2, factor):
          sides = []
          if dy == dx // 2:
            sides.append(TileSide.TOP)
            base_tile.shape = (TileShape.SMALL_1 if (dx + factor) % 2 else
                               TileShape.BIG_1)
          else:
            base_tile.shape = TileShape.FULL
          if dx == 0: sides.append(TileSide.LEFT)
          if dy + 1 == factor: sides.append(TileSide.BOTTOM)
          tile = copy.deepcopy(base_tile)
          tile._copy_sides(self, sides)
          result.append((dx, dy, tile))
    elif self.shape == TileShape.SMALL_1:
      for dx in range(factor):
        for dy in range((factor + dx) // 2, factor):
          sides = []
          if dy == (factor + dx) // 2:
            sides.append(TileSide.TOP)
            base_tile.shape = (TileShape.SMALL_1 if (dx + factor) % 2 else
                               TileShape.BIG_1)
          else:
            base_tile.shape = TileShape.FULL
          if dy + 1 == factor: sides.append(TileSide.BOTTOM)
          tile = copy.deepcopy(base_tile)
          tile._copy_sides(self, sides)
          result.append((dx, dy, tile))
    elif self.shape == TileShape.HALF_A:
      for dx in range(factor):
        for dy in range(dx, factor):
          sides = []
          if dx == dy:
            sides.append(TileSide.TOP)
            base_tile.shape = TileShape.HALF_A
          else:
            base_tile.shape = TileShape.FULL
          if dx == 0: sides.append(TileSide.LEFT)
          if dy + 1 == factor: sides.append(TileSide.BOTTOM)
          tile = copy.deepcopy(base_tile)
          tile._copy_sides(self, sides)
          result.append((dx, dy, tile))
    elif self.shape == TileShape.BIG_5 or self.shape == TileShape.SMALL_5:
      self.transform([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
      oresult = self.upscale(factor)
      rmat = [[-1, 0, factor - 1], [0, 1, 0], [0, 0, 1]]
      self.transform(rmat)

      result = []
      for (dx, dy, tile) in oresult:
        tile.transform(rmat)
        result.append((dx * rmat[0][0] + dy * rmat[0][1] + rmat[0][2],
                       dx * rmat[1][0] + dy * rmat[1][1] + rmat[1][2],
                       tile))
    else:
      self.transform([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
      oresult = self.upscale(factor)
      rmat = [[0, 1, 0], [-1, 0, factor - 1], [0, 0, 1]]
      self.transform(rmat)

      result = []
      for (dx, dy, tile) in oresult:
        tile.transform(rmat)
        result.append((dx * rmat[0][0] + dy * rmat[0][1] + rmat[0][2],
                       dx * rmat[1][0] + dy * rmat[1][1] + rmat[1][2],
                       tile))
    return result
