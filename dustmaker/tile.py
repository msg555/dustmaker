"""
Module defining the tile respresentation in dustmaker.
"""
import copy
import math
from typing import Iterable, List, Optional, Tuple

from .enums import TileShape, TileSide, TileSpriteSet

TxMatrix = List[List[float]]

"""
       Tile byte layout notes
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


def _pack_tile_data(
    edge_bits: List[int],
    edge_angle: List[int],
    sprite_set: int,
    sprite_tile: int,
    sprite_palette: int,
) -> bytes:
    """Pack the dustmaker respresentation back into the binary representation"""
    assert len(edge_bits) == 4
    assert len(edge_angle) == 4

    tile_data = [0 for _ in range(12)]
    for side, val in enumerate(edge_bits):
        assert 0 <= val <= 0xF
        offsets = (0 + side, 4 + side, 8 + 2 * side, 9 + 2 * side)
        for i, off in enumerate(offsets):
            if val & 1 << i:
                tile_data[off >> 3] |= 1 << (off & 7)

    for side, angle in enumerate(edge_angle):
        assert 0 <= angle <= 0xFFFF
        tile_data[2 + side * 2] = angle & 0xFF
        tile_data[3 + side * 2] = angle >> 8

    assert 0 <= sprite_set <= 0xF
    assert 0 <= sprite_tile <= 0xFF
    assert 0 <= sprite_palette <= 0xF

    tile_data[10] = sprite_set + (sprite_palette << 4)
    tile_data[11] = sprite_tile

    return bytes(tile_data)


def _unpack_tile_data(
    tile_data: bytes,
) -> Tuple[List[int], List[int], TileSpriteSet, int, int]:
    """Unpack tile data into the representation used by dustmaker."""
    assert len(tile_data) == 12

    # Extract the edge bits
    edge_bits = []
    for side in range(4):
        val = 0
        offsets = (0 + side, 4 + side, 8 + 2 * side, 9 + 2 * side)
        for i, off in enumerate(offsets):
            if tile_data[off >> 3] & (1 << (off & 7)):
                val |= 1 << i
        edge_bits.append(val)

    edge_angles = [
        tile_data[2 + side * 2] + (tile_data[3 + side * 2] << 8) for side in range(4)
    ]
    sprite_set = TileSpriteSet(tile_data[10] & 0xF)
    sprite_tile = tile_data[11]
    sprite_palette = tile_data[10] >> 4

    return edge_bits, edge_angles, sprite_set, sprite_tile, sprite_palette


def _pack_dust_data(
    filth_sprite_sets: List[TileSpriteSet],
    filth_spikes: List[bool],
    filth_angles: List[Tuple[int, int]],
    filth_caps: List[int],
) -> bytes:
    """Pack the dustmaker respresentation back into the binary representation"""
    assert len(filth_sprite_sets) == 4
    assert len(filth_spikes) == 4
    assert len(filth_angles) == 4
    assert len(filth_caps) == 4

    dust_data = [0 for _ in range(12)]

    for side in range(4):
        sset, spike, angle, cap = (
            filth_sprite_sets[side],
            filth_spikes[side],
            filth_angles[side],
            filth_caps[side],
        )
        assert 0 <= sset <= 0xF
        assert isinstance(spike, bool)
        assert 0 <= angle[0] <= 0xFF
        assert 0 <= angle[1] <= 0xFF
        assert 0 <= cap <= 0x3

        off = 4 * side
        dust_data[off >> 3] |= (sset | (0x8 if spike else 0)) << (off & 0x7)
        dust_data[2 + side * 2], dust_data[3 + side * 2] = angle
        dust_data[10] |= cap << (2 * side)

    return bytes(dust_data)


def _unpack_dust_data(
    dust_data: bytes,
) -> Tuple[List[TileSpriteSet], List[bool], List[Tuple[int, int]], List[int]]:
    """Unpack dust data into the representation used by dustmaker."""
    assert len(dust_data) == 12

    filth_sprite_sets = []
    filth_spikes = []
    filth_caps = []
    for side in range(4):
        off = 4 * side
        val = dust_data[off >> 3] >> (off & 0x7)
        filth_sprite_sets.append(TileSpriteSet(val & 0x7))
        filth_spikes.append(bool(val & 0x8))
        filth_caps.append((dust_data[10] >> (2 * side)) & 0x3)

    filth_angles = [
        (dust_data[2 + side * 2], dust_data[3 + side * 2]) for side in range(4)
    ]
    return filth_sprite_sets, filth_spikes, filth_angles, filth_caps


class Tile:
    """Represents a single tile in a Dustforce level.  Positional information
    is stored within Map and not in this Tile object.

    Fields
      All "List" fields are of length 4 mapping tile sides to the particular
      field value.

      shape: TileShape - The shape of this particular tile.

      edge_bits: List[4 bit int] - These are the collision bits for each side
          of the tile. Use 0 for no collision and 0xF for normal collisions. Any
          other settings have undocumented behavior.

      edge_angle: List[16 bit int] - The angle of the side of each edge. This
          controls how edges are drawn and is ignored if the edge bits are not
          set for the given side.

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
        tile_data: Optional[bytes] = None,
        dust_data: Optional[bytes] = None
    ) -> None:
        """Initialize a vanilla virtual tile of the given shape."""
        self.shape = shape
        self.edge_bits = [0 for _ in range(4)]
        self.edge_angles = [0 for _ in range(4)]
        self.sprite_set = TileSpriteSet.TUTORIAL
        self.sprite_tile = 1
        self.sprite_palette = 0
        self.filth_sprite_sets = [TileSpriteSet.NONE_0 for _ in range(4)]
        self.filth_spikes = [False for _ in range(4)]
        self.filth_angles = [(0, 0) for _ in range(4)]
        self.filth_caps = [0 for _ in range(4)]

        if tile_data is not None:
            self._set_tile_data(tile_data)
        if dust_data is not None:
            self._set_dust_data(dust_data)

    def _set_tile_data(self, tile_data: bytes) -> None:
        """Helper method to unpack the packed tile data"""
        (
            self.edge_bits,
            self.edge_angle,
            self.sprite_set,
            self.sprite_tile,
            self.sprite_palette,
        ) = _unpack_tile_data(tile_data)

    def _get_tile_data(self) -> bytes:
        """Helper method to pack the tile data"""
        return _pack_tile_data(
            self.edge_bits,
            self.edge_angle,
            self.sprite_set,
            self.sprite_tile,
            self.sprite_palette,
        )

    def _set_dust_data(self, dust_data: bytes) -> None:
        """Helper method to unpack the packed dust data"""
        (
            self.filth_sprite_sets,
            self.filth_spikes,
            self.filth_angles,
            self.filth_caps,
        ) = _unpack_dust_data(dust_data)

    def _get_dust_data(self) -> bytes:
        """Helper method to pack the dust data"""
        return _pack_dust_data(
            self.filth_sprite_sets,
            self.filth_spikes,
            self.filth_angles,
            self.filth_caps,
        )

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
        return any(st != TileSpriteSet.NONE_0 for st in self.filth_sprite_sets)

    def is_dustblock(self) -> bool:
        """
        Returns true if the tile is a dustblock.
        """
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
            if self.shape == TileShape.FULL:
                pass
            elif self.shape <= TileShape.SMALL_8:
                self.shape = TileShape(1 + ((self.shape - TileShape.BIG_1) ^ 8) % 16)
            else:
                self.shape = TileShape(17 + ((self.shape - TileShape.HALF_A) ^ 3))
        angle = int(round(math.atan2(mat[1][1], mat[1][0]) / math.pi * 2))
        angle = (-angle + 1) & 0x3

        if self.shape == TileShape.FULL:
            pass
        elif self.shape <= TileShape.SMALL_4:
            self.shape = TileShape(1 + ((self.shape - TileShape.BIG_1) + angle * 2) % 8)
        elif self.shape <= TileShape.SMALL_8:
            self.shape = TileShape(9 + ((self.shape - TileShape.BIG_5) - angle * 2) % 8)
        else:
            self.shape = TileShape(17 + ((self.shape - TileShape.HALF_A) + angle) % 4)

        edge_data = []
        for side in SHAPE_ORDERED_SIDES[oshape]:
            edge_data.append(
                (
                    self.edge_bits[side],
                    self.edge_angle[side],
                    self.filth_sprite_sets[side],
                    self.filth_spikes[side],
                    self.filth_angles[side],
                    self.filth_caps[side],
                )
            )
        for side in TileSide:
            (
                self.edge_bits[side],
                self.edge_angle[side],
                self.filth_sprite_sets[side],
                self.filth_spikes[side],
                self.filth_angles[side],
                self.filth_caps[side],
            ) = (
                0,
                0,
                TileSpriteSet.NONE_0,
                False,
                (0, 0),
                0,
            )
        for (i, side) in enumerate(SHAPE_ORDERED_SIDES[self.shape]):
            if self.shape == TileShape.FULL:
                i = i + angle & 3
                if flipped:
                    i = -i & 3
            (
                self.edge_bits[side],
                self.edge_angle[side],
                self.filth_sprite_sets[side],
                self.filth_spikes[side],
                self.filth_angles[side],
                self.filth_caps[side],
            ) = edge_data[i]

    def _copy_sides(self, tile: "Tile", sides: Iterable[TileSide]) -> None:
        """Copy some of the edge bits from another tile"""
        for side in sides:
            (
                self.edge_bits[side],
                self.edge_angle[side],
                self.filth_sprite_sets[side],
                self.filth_spikes[side],
                self.filth_angles[side],
                self.filth_caps[side],
            ) = (
                tile.edge_bits[side],
                tile.edge_angle[side],
                tile.filth_sprite_sets[side],
                tile.filth_spikes[side],
                tile.filth_angles[side],
                tile.filth_caps[side],
            )

    def upscale(self, factor: int) -> List[Tuple[int, int, "Tile"]]:
        """
        Upscales a tile, returning a list of (dx, dy, tile) tuples giving
        the relative position of the upscaled tiles and the new tile shape.
        """
        result = []

        base_tile = Tile(TileShape.FULL)
        base_tile.sprite_set = self.sprite_set
        base_tile.sprite_tile = self.sprite_tile
        base_tile.sprite_palette = self.sprite_palette
        for side in TileSide:
            base_tile.edge_bits[side] = 0

        if self.shape == TileShape.FULL:
            for dx in range(factor):
                for dy in range(factor):
                    sides = []
                    if dx == 0:
                        sides.append(TileSide.LEFT)
                    if dx + 1 == factor:
                        sides.append(TileSide.RIGHT)
                    if dy == 0:
                        sides.append(TileSide.TOP)
                    if dy + 1 == factor:
                        sides.append(TileSide.BOTTOM)
                    tile = copy.deepcopy(base_tile)
                    tile._copy_sides(self, sides)
                    result.append((dx, dy, tile))

        elif self.shape == TileShape.BIG_1:
            for dx in range(factor):
                for dy in range(dx // 2, factor):
                    sides = []
                    if dy == dx // 2:
                        sides.append(TileSide.TOP)
                        base_tile.shape = (
                            TileShape.SMALL_1 if (dx + factor) % 2 else TileShape.BIG_1
                        )
                    else:
                        base_tile.shape = TileShape.FULL
                    if dx == 0:
                        sides.append(TileSide.LEFT)
                    if dy + 1 == factor:
                        sides.append(TileSide.BOTTOM)
                    tile = copy.deepcopy(base_tile)
                    tile._copy_sides(self, sides)
                    result.append((dx, dy, tile))
        elif self.shape == TileShape.SMALL_1:
            for dx in range(factor):
                for dy in range((factor + dx) // 2, factor):
                    sides = []
                    if dy == (factor + dx) // 2:
                        sides.append(TileSide.TOP)
                        base_tile.shape = (
                            TileShape.SMALL_1 if (dx + factor) % 2 else TileShape.BIG_1
                        )
                    else:
                        base_tile.shape = TileShape.FULL
                    if dy + 1 == factor:
                        sides.append(TileSide.BOTTOM)
                    tile = copy.deepcopy(base_tile)
                    tile._copy_sides(self, sides)
                    result.append((dx, dy, tile))
        elif self.shape == TileShape.HALF_A:
            for dx in range(factor):
                for dy in range(dx, factor):
                    sides = []
                    if dx == dy:
                        sides.append(TileSide.TOP)
                        # pylint: disable=redefined-variable-type
                        base_tile.shape = TileShape.HALF_A
                    else:
                        base_tile.shape = TileShape.FULL
                    if dx == 0:
                        sides.append(TileSide.LEFT)
                    if dy + 1 == factor:
                        sides.append(TileSide.BOTTOM)
                    tile = copy.deepcopy(base_tile)
                    tile._copy_sides(self, sides)
                    result.append((dx, dy, tile))
        elif self.shape == TileShape.BIG_5 or self.shape == TileShape.SMALL_5:
            self.transform([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
            oresult = self.upscale(factor)
            rmat = [[-1, 0, factor - 1], [0, 1, 0], [0, 0, 1]]
            self.transform(rmat)  # type: ignore

            result = []
            for (dx, dy, tile) in oresult:
                tile.transform(rmat)  # type: ignore
                result.append(
                    (
                        dx * rmat[0][0] + dy * rmat[0][1] + rmat[0][2],
                        dx * rmat[1][0] + dy * rmat[1][1] + rmat[1][2],
                        tile,
                    )
                )
        else:
            self.transform([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
            oresult = self.upscale(factor)
            rmat = [[0, 1, 0], [-1, 0, factor - 1], [0, 0, 1]]
            self.transform(rmat)  # type: ignore

            result = []
            for (dx, dy, tile) in oresult:
                tile.transform(rmat)  # type: ignore
                result.append(
                    (
                        dx * rmat[0][0] + dy * rmat[0][1] + rmat[0][2],
                        dx * rmat[1][0] + dy * rmat[1][1] + rmat[1][2],
                        tile,
                    )
                )
        return result


# Full - Clockwise from top
# Small/Big/Half - Clockwise from hyp. (ccw from mirrored)
SHAPE_ORDERED_SIDES = (
    (0, 2, 1, 3),
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


# Give the maximal edge bits of each tile shape
TILE_MAXIMAL_BITS = (
    (
        15,
        15,
        15,
        15,
    ),  # TileShape.FULL:
    (
        7,
        15,
        15,
        0,
    ),  # TileShape.BIG_1:
    (
        11,
        15,
        0,
        0,
    ),  # TileShape.SMALL_1:
    (
        15,
        0,
        15,
        7,
    ),  # TileShape.BIG_2:
    (
        0,
        0,
        15,
        11,
    ),  # TileShape.SMALL_2:
    (
        15,
        11,
        0,
        15,
    ),  # TileShape.BIG_3:
    (
        15,
        7,
        0,
        0,
    ),  # TileShape.SMALL_3:
    (
        0,
        15,
        11,
        15,
    ),  # TileShape.BIG_4:
    (
        0,
        0,
        7,
        15,
    ),  # TileShape.SMALL_4:
    (
        11,
        15,
        0,
        15,
    ),  # TileShape.BIG_5:
    (
        7,
        15,
        0,
        0,
    ),  # TileShape.SMALL_5:
    (
        15,
        0,
        7,
        15,
    ),  # TileShape.BIG_6:
    (
        0,
        0,
        11,
        15,
    ),  # TileShape.SMALL_6:
    (
        15,
        7,
        15,
        0,
    ),  # TileShape.BIG_7:
    (
        15,
        11,
        0,
        0,
    ),  # TileShape.SMALL_7:
    (
        0,
        15,
        15,
        11,
    ),  # TileShape.BIG_8:
    (
        0,
        0,
        15,
        7,
    ),  # TileShape.SMALL_8:
    (
        15,
        15,
        15,
        0,
    ),  # TileShape.HALF_A:
    (
        15,
        15,
        15,
        0,
    ),  # TileShape.HALF_B:
    (
        15,
        15,
        0,
        15,
    ),  # TileShape.HALF_C:
    (
        15,
        15,
        0,
        15,
    ),  # TileShape.HALF_D:
)
