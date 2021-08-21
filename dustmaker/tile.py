"""
Module defining the tile respresentation in dustmaker.
"""
import copy
from dataclasses import dataclass
from enum import IntEnum
import math
from typing import List, Generator, Optional, Tuple

TxMatrix = List[List[float]]


def matmul(lhs: TxMatrix, rhs: TxMatrix) -> TxMatrix:
    """Multiply two matrixes. Intended for transformation matrixes but works
    for general matrix multiplication.

    Arguments:
        lhs (TxMatrix): left matrix to multiply
        rhs (TxMatrix): right matrix to multiply

    Returns:
        The multiplied matrix
    """
    return [
        [
            sum(lhs[i][k] * rhs[k][j] for k in range(len(lhs[0])))
            for j in range(len(rhs[0]))
        ]
        for i in range(len(lhs))
    ]


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


@dataclass
class TileEdgeData:
    """Container class for data stored on each tile edge."""

    solid: bool = False
    visible: bool = False
    caps: Tuple[bool, bool] = (False, False)
    angles: Tuple[int, int] = (0, 0)
    filth_sprite_set: TileSpriteSet = TileSpriteSet.NONE_0
    filth_spike: bool = False
    filth_caps: Tuple[bool, bool] = (False, False)
    filth_angles: Tuple[int, int] = (0, 0)


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


class Tile:
    """Represents a single tile in a Dustforce level.  Positional information
    is stored within Map and not in this Tile object.

    Fields
      All "List" fields are of length 4 mapping tile sides to the particular
      field value.

      shape: TileShape - The shape of this particular tile.

      tile_flags: 3 bit int
        Bit 1 - "solid slope flag" (probably ignored)
        Bit 2 - "visible flag" (probably ignored)
        Bit 3 - solid flag

      edge_bits: List[4 bit int] - These are the collision bits for each side
          of the tile. From engine source:
            Bit 0 - solid flag
            Bit 1 - visible flag
            Bit 2,3 - "2 bits for ends of each edge". These have been normalized
                      to be in clockwise order relative the center of the tile.
                      (i.e. for the top edge this is left, right bits)

      edge_angles: List[Tuple[signed byte, signed byte]] - The angle of the side of each edge.
          The edges for a side are listed in clockwise order relative the
          center of the tile.

      sprite_set: TileSpriteSet - The sprite set this tile comes from. (e.g.
          forest, mansion)

      sprite_tile: int - The index of the specific tile within this sprite set (e.g.
          grass, dirt)

      sprite_palette: int - The color variant of this tile.

      filth_sprite_sets: List[TileSpriteSet] - Controls which sprite set that
          filth/spikes attached to the edge come from (e.g. forest, mansion)

      filth_spikes: List[bool] - Controls wether the filth is dust or spikes.

      filth_angles: List[16 bit int] - Controls the draw angle of the
          filth/spikes on the given edge.

      filth_caps: List[2 bit int] - Dunno

      For sprite_set, sprite_tile, and sprite_palette see
      https://github.com/cmann1/PropUtils/tree/master/files/tiles_reference for
      a visual respresentation to help you select which values you want.
    """

    def __init__(
        self,
        shape: TileShape,
        *,
        tile_flags: int = 0x4,
        tile_data: Optional[bytes] = None,
        dust_data: Optional[bytes] = None,
    ) -> None:
        """Initialize a vanilla virtual tile of the given shape."""
        self.shape = shape
        self.tile_flags = tile_flags
        self.edge_data = [TileEdgeData() for _ in TileSide]
        self.sprite_set = TileSpriteSet.TUTORIAL
        self.sprite_tile = 1
        self.sprite_palette = 0

        if tile_data is not None:
            self._unpack_tile_data(tile_data)
        if dust_data is not None:
            self._unpack_dust_data(dust_data)

    def get_sprite_tuple(self) -> Tuple[TileSpriteSet, int, int]:
        """Convenience method for getting a tuple that describes the sprite
        of a tile for easy sprite comparisons.

        Returns:
            (sprite_set, sprite_tile, sprite_palette) (TileSpriteSet, int, int):
                the sprite set, tile, and palette of this tile.
        """
        return self.sprite_set, self.sprite_tile, self.sprite_palette

    def set_sprite_tuple(self, sprite_tuple: Tuple[TileSpriteSet, int, int]) -> None:
        """Convenience method for setting sprite information in the same format
        as :meth:`get_sprite_tuple`.

        Arguments:
            sprite_tuple (TileSpriteSet, int, int): Sprite set, tile, and palette
                information.
        """
        self.sprite_set, self.sprite_tile, self.sprite_palette = sprite_tuple

    @property
    def sprite_path(self) -> str:
        """Returns the palette index associated with this tile.  You may
        retrieve the complete game sprites listing from
        https://www.dropbox.com/s/jm37ew9p74olgca/sprites.zip?dl=0
        """
        return "area/%s/tiles/tile%d_%d_0001.png" % (
            self.sprite_set.name.lower(),
            self.sprite_tile,
            self.sprite_palette + 1,
        )

    def has_filth(self) -> bool:
        """Returns true if there is filth attached to any edges of this tile"""
        return any(
            edge.filth_sprite_set != TileSpriteSet.NONE_0 for edge in self.edge_data
        )

    def is_dustblock(self) -> bool:
        """Returns true if the tile is a dustblock."""
        return {
            TileSpriteSet.MANSION: 21,
            TileSpriteSet.FOREST: 13,
            TileSpriteSet.CITY: 6,
            TileSpriteSet.LABORATORY: 9,
            TileSpriteSet.TUTORIAL: 2,
        }.get(self.sprite_set, -1) == self.sprite_tile

    def transform(self, mat: TxMatrix) -> None:
        """
        Performs a flip and rotation as dictated by the tranformation matrix.
        Does not do any kind of scaling. Use upscale() if that behavior is
        desired.
        """
        oshape = self.shape
        flipped = mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0] < 0
        if flipped:
            # horizontally flip
            if self.shape == TileShape.FULL:
                self.edge_data[TileSide.LEFT], self.edge_data[TileSide.RIGHT] = (
                    self.edge_data[TileSide.RIGHT],
                    self.edge_data[TileSide.LEFT],
                )
            elif self.shape <= TileShape.SMALL_8:
                self.shape = TileShape(1 + ((self.shape - TileShape.BIG_1) ^ 8) % 16)
            else:
                self.shape = TileShape(17 + ((self.shape - TileShape.HALF_A) ^ 3))

            # flips swap clockwise to counterclockwise, reverse directed data
            for edge in self.edge_data:
                edge.caps = edge.caps[::-1]
                edge.filth_caps = edge.filth_caps[::-1]
                edge.angles = (-edge.angles[1], -edge.angles[0])
                edge.filth_angles = (-edge.filth_angles[1], -edge.filth_angles[0])

        angle = int(
            round(
                math.atan2(mat[1][1], (-1 if flipped else 1) * mat[1][0]) / math.pi * 2
            )
        )
        angle = (-angle + 1) & 0x3

        if self.shape == TileShape.FULL:
            pass
        elif self.shape <= TileShape.SMALL_4:
            self.shape = TileShape(1 + ((self.shape - TileShape.BIG_1) + angle * 2) % 8)
        elif self.shape <= TileShape.SMALL_8:
            self.shape = TileShape(9 + ((self.shape - TileShape.BIG_5) - angle * 2) % 8)
        else:
            self.shape = TileShape(17 + ((self.shape - TileShape.HALF_A) + angle) % 4)

        og_edge_data = [
            copy.deepcopy(self.edge_data[side]) for side in SHAPE_ORDERED_SIDES[oshape]
        ]
        self.edge_data = [TileEdgeData() for _ in TileSide]

        for i, side in enumerate(SHAPE_ORDERED_SIDES[self.shape]):
            if self.shape == TileShape.FULL:
                i = (i - angle) & 3
            self.edge_data[side] = og_edge_data[i]

    def upscale(self, factor: int) -> Generator[Tuple[int, int, "Tile"], None, None]:
        """
        Upscales a tile, returning a list of (dx, dy, tile) tuples giving
        the relative position of the upscaled tiles and the new tile shape.
        """
        cw_index = (0, 2, 3, 1)

        def _tuple_set(data: Tuple, ind: int, value) -> Tuple:
            return tuple((value if i == ind else x) for i, x in enumerate(data))

        def _copy_side(dx: int, dy: int, tile: Tile, side: TileSide):
            """Copies a side from self into the upscaled tile. Adjust the
            caps if the edge does not leave the upscaled tile boundary.
            """
            edge_data = copy.deepcopy(self.edge_data[side])

            cw_ind = cw_index[side]
            for dr in range(2):
                vert_a = SHAPE_VERTEXES[tile.shape][(cw_ind + 1 - dr) & 0x3]
                vert_b = SHAPE_VERTEXES[tile.shape][(cw_ind + dr) & 0x3]
                x = 2 * dx + vert_b[0]
                y = 2 * dy + vert_b[1]
                if vert_a[0] != vert_b[0] and x in (0, factor * 2):
                    continue
                if vert_a[1] != vert_b[1] and y in (0, factor * 2):
                    continue

                edge_data.caps = _tuple_set(edge_data.caps, dr, False)  # type: ignore
                edge_data.angles = _tuple_set(edge_data.angles, dr, 0)  # type: ignore
                edge_data.filth_caps = _tuple_set(edge_data.filth_caps, dr, False)  # type: ignore
                edge_data.filth_angles = _tuple_set(edge_data.filth_angles, dr, 0)  # type: ignore

            tile.edge_data[side] = edge_data

        if self.shape == TileShape.FULL:
            for dx in range(factor):
                for dy in range(factor):
                    tile = Tile(TileShape.FULL)
                    tile.set_sprite_tuple(self.get_sprite_tuple())

                    if dx == 0:
                        _copy_side(dx, dy, tile, TileSide.LEFT)
                    if dx + 1 == factor:
                        _copy_side(dx, dy, tile, TileSide.RIGHT)
                    if dy == 0:
                        _copy_side(dx, dy, tile, TileSide.TOP)
                    if dy + 1 == factor:
                        _copy_side(dx, dy, tile, TileSide.BOTTOM)

                    yield dx, dy, tile

        elif self.shape in (TileShape.BIG_1, TileShape.SMALL_1):
            for dx in range(factor):
                ddx = dx + (factor if self.shape == TileShape.SMALL_1 else 0)
                for dy in range(ddx // 2, factor):
                    tile = Tile(TileShape.FULL)
                    tile.set_sprite_tuple(self.get_sprite_tuple())

                    if dy == ddx // 2:
                        tile.shape = TileShape.SMALL_1 if ddx % 2 else TileShape.BIG_1
                        _copy_side(dx, dy, tile, TileSide.TOP)
                    if dx == 0:
                        _copy_side(dx, dy, tile, TileSide.LEFT)
                    if dy + 1 == factor:
                        _copy_side(dx, dy, tile, TileSide.BOTTOM)

                    yield dx, dy, tile

        elif self.shape == TileShape.HALF_A:
            for dx in range(factor):
                for dy in range(dx, factor):
                    tile = Tile(TileShape.FULL)
                    tile.set_sprite_tuple(self.get_sprite_tuple())

                    if dx == dy:
                        tile.shape = TileShape.HALF_A
                        _copy_side(dx, dy, tile, TileSide.TOP)
                    if dx == 0:
                        _copy_side(dx, dy, tile, TileSide.LEFT)
                    if dy + 1 == factor:
                        _copy_side(dx, dy, tile, TileSide.BOTTOM)

                    yield dx, dy, tile

        else:
            # Otherwise transform the tile into one of the above handled cases
            # and transform the result back.
            new_shape = self.shape

            hflip = False
            if TileShape.BIG_5 <= new_shape <= TileShape.SMALL_8:
                # horizontal flip
                hflip = True
                new_shape = TileShape(new_shape - 8)

            if TileShape.BIG_1 <= new_shape <= TileShape.SMALL_4:
                rots = (new_shape - TileShape.BIG_1) // 2
            else:  # Half tile
                rots = new_shape - TileShape.HALF_A

            # Calculate rotation matrix and inverse
            cs = (1, 0, -1, 0)
            sn = (0, 1, 0, -1)
            mat = [[cs[rots], sn[rots], 0], [-sn[rots], cs[rots], 0], [0, 0, 1]]
            imat = [[cs[rots], -sn[rots], 0], [sn[rots], cs[rots], 0], [0, 0, 1]]

            # Apply horizontal flip
            if hflip:
                mat[0][0] *= -1
                mat[1][0] *= -1
                imat[0][0] *= -1
                imat[0][1] *= -1

            # Fix up offset so transformed positions stay in upscale square.
            for matrix in (mat, imat):
                for row in matrix:
                    if sum(row) < 0:
                        row[2] += factor - 1

            # Copy tile and transform it.
            ntile = copy.deepcopy(self)
            ntile.transform(mat)  # type: ignore
            assert ntile.shape in (TileShape.HALF_A, TileShape.BIG_1, TileShape.SMALL_1)

            # For each of the new upscaled tiles inverse the transformation.
            for dx, dy, tile in ntile.upscale(factor):
                tile.transform(imat)  # type: ignore
                yield (
                    dx * imat[0][0] + dy * imat[0][1] + imat[0][2],
                    dx * imat[1][0] + dy * imat[1][1] + imat[1][2],
                    tile,
                )

    def _pack_tile_data(self) -> bytes:
        """Pack the dustmaker respresentation back into the binary representation"""
        tile_data = [0 for _ in range(12)]
        for side, edge in enumerate(self.edge_data):
            vals = [edge.solid, edge.visible, *edge.caps]
            offsets = [0 + side, 4 + side, 8 + 2 * side, 9 + 2 * side]

            if side in (TileSide.LEFT, TileSide.BOTTOM):
                # Need to swap the edge bit order to match IO order
                offsets[2], offsets[3] = offsets[3], offsets[2]

            for val, off in zip(vals, offsets):
                if val:
                    tile_data[off >> 3] |= 1 << (off & 7)

            assert -0x80 <= edge.angles[0] <= 0x7F and -0x80 <= edge.angles[1] <= 0x7F
            v0, v1 = edge.angles
            if side in (TileSide.LEFT, TileSide.BOTTOM):
                v0, v1 = v1, v0
            tile_data[2 + side * 2] = v0 & 0xFF
            tile_data[3 + side * 2] = v1 & 0xFF

        assert 0 <= self.sprite_set <= 0xF
        assert 0 <= self.sprite_tile <= 0xFF
        assert 0 <= self.sprite_palette <= 0xF

        tile_data[10] = self.sprite_set + (self.sprite_palette << 4)
        tile_data[11] = self.sprite_tile

        return bytes(tile_data)

    def _unpack_tile_data(self, tile_data: bytes) -> None:
        """Unpack tile data into the representation used by dustmaker."""
        assert len(tile_data) == 12

        # Extract the edge bits
        for side, edge in enumerate(self.edge_data):

            def test_offset(off: int) -> bool:
                return bool(tile_data[off >> 3] & (1 << (off & 7)))

            edge.solid = test_offset(0 + side)
            edge.visible = test_offset(4 + side)
            edge.caps = (test_offset(8 + 2 * side), test_offset(9 + 2 * side))
            if side in (TileSide.LEFT, TileSide.BOTTOM):
                edge.caps = (edge.caps[1], edge.caps[0])

            v0, v1 = tile_data[2 + side * 2], tile_data[3 + side * 2]
            if v0 >= 0x80:
                v0 -= 0x100
            if v1 >= 0x80:
                v1 -= 0x100
            if side in (TileSide.LEFT, TileSide.BOTTOM):
                v0, v1 = v1, v0
            edge.angles = (v0, v1)

        self.sprite_set = TileSpriteSet(tile_data[10] & 0xF)
        self.sprite_tile = tile_data[11]
        self.sprite_palette = tile_data[10] >> 4

    def _pack_dust_data(self) -> bytes:
        """Pack the dustmaker respresentation back into the binary representation"""
        dust_data = [0 for _ in range(12)]

        for side, edge in enumerate(self.edge_data):
            sset, spike, caps, angles = (
                edge.filth_sprite_set,
                edge.filth_spike,
                edge.filth_caps,
                edge.filth_angles,
            )
            assert 0 <= sset <= 0xF
            assert -0x80 <= angles[0] <= 0x7F
            assert -0x80 <= angles[1] <= 0x7F

            # Normalize for Dustforce binary format
            if side in (TileSide.LEFT, TileSide.BOTTOM):
                caps = caps[::-1]
                angles = angles[::-1]

            off = 4 * side
            dust_data[off >> 3] |= (sset | (0x8 if spike else 0)) << (off & 0x7)
            dust_data[2 + side * 2] = angles[0] & 0xFF
            dust_data[3 + side * 2] = angles[1] & 0xFF
            if caps[0]:
                dust_data[10] |= 1 << (2 * side)
            if caps[1]:
                dust_data[10] |= 2 << (2 * side)

        return bytes(dust_data)

    def _unpack_dust_data(self, dust_data: bytes) -> None:
        """Unpack dust data into the representation used by dustmaker."""
        assert len(dust_data) == 12

        for side, edge in enumerate(self.edge_data):
            off = 4 * side
            val = dust_data[off >> 3] >> (off & 0x7)
            edge.filth_sprite_set = TileSpriteSet(val & 0x7)
            edge.filth_spike = bool(val & 0x8)
            edge.filth_caps = (
                bool((dust_data[10] >> (2 * side)) & 0x1),
                bool((dust_data[10] >> (2 * side)) & 0x2),
            )

            v0, v1 = dust_data[2 + side * 2], dust_data[3 + side * 2]
            if v0 >= 0x80:
                v0 -= 0x100
            if v1 >= 0x80:
                v1 -= 0x100
            edge.filth_angles = (v0, v1)

            # Normalize for Dustforce binary format
            if side in (TileSide.LEFT, TileSide.BOTTOM):
                edge.filth_caps = edge.filth_caps[::-1]
                edge.filth_angles = edge.filth_angles[::-1]


# Full - Clockwise from top
# Small/Big/Half - Clockwise from hyp. (ccw from mirrored)
SHAPE_ORDERED_SIDES = tuple(
    tuple(TileSide(x) for x in y)
    for y in (
        (0, 3, 1, 2),
        (0, 1, 2),
        (0, 1),
        (3, 2, 0),
        (3, 2),
        (1, 0, 3),
        (1, 0),
        (2, 3, 1),
        (2, 3),
        (0, 1, 3),
        (0, 1),
        (2, 3, 0),
        (2, 3),
        (1, 0, 2),
        (1, 0),
        (3, 2, 1),
        (3, 2),
        (0, 1, 2),
        (1, 2, 0),
        (1, 0, 3),
        (0, 3, 1),
    )
)


# top-left, top-right, bottom-right, bottom-left coordinates
SHAPE_VERTEXES = (
    ((0, 0), (2, 0), (2, 2), (0, 2)),  # FULL
    # Slants are rotations of each other
    ((0, 0), (2, 1), (2, 2), (0, 2)),  # BIG_1
    ((0, 1), (2, 2), (2, 2), (0, 2)),  # SMALL_1
    ((0, 0), (2, 0), (1, 2), (0, 2)),  # BIG_2
    ((0, 0), (1, 0), (0, 2), (0, 2)),  # SMALL_2
    ((0, 0), (2, 0), (2, 2), (0, 1)),  # BIG_3
    ((0, 0), (2, 0), (2, 1), (0, 0)),  # SMALL_3
    ((1, 0), (2, 0), (2, 2), (0, 2)),  # BIG_4
    ((2, 0), (2, 0), (2, 2), (1, 2)),  # SMALL_4
    ((0, 1), (2, 0), (2, 2), (0, 2)),  # BIG_5
    ((0, 2), (2, 1), (2, 2), (0, 2)),  # SMALL_5
    ((0, 0), (2, 0), (2, 2), (1, 2)),  # BIG_6
    ((1, 0), (2, 0), (2, 2), (2, 2)),  # SMALL_6
    ((0, 0), (2, 0), (2, 1), (0, 2)),  # BIG_7
    ((0, 0), (2, 0), (2, 0), (0, 1)),  # SMALL_7
    ((0, 0), (1, 0), (2, 2), (0, 2)),  # BIG_8
    ((0, 0), (0, 0), (1, 2), (0, 2)),  # SMALL_8
    # Slopes are special because they always have a top and bottom so they
    # don't simply rotate between each one. The repeated coordinate is
    # always placed so it makes a left or right edge null.
    ((0, 0), (2, 2), (2, 2), (0, 2)),  # HALF_A
    ((0, 0), (2, 0), (2, 0), (0, 2)),  # HALF_B
    ((0, 0), (2, 0), (2, 2), (0, 0)),  # HALF_C
    ((0, 2), (2, 0), (2, 2), (0, 2)),  # HALF_D
)

# SIDE_CLOCKWISE_INDEX[side] gives
SIDE_CLOCKWISE_INDEX = (
    0,  # TOP
    2,  # BOTTOM
    3,  # LEFT
    1,  # RIGHT
)
