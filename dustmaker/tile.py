"""
Module defining the tile respresentation in dustmaker.
"""
import copy
from dataclasses import dataclass
from enum import IntEnum
import math
from typing import Generator, Optional, Tuple

from .transform import TxMatrix


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
    """Used to index the sides of a tile. This is the indexing done by the
    Dustforce engine itself."""

    TOP = 0
    BOTTOM = 1
    LEFT = 2
    RIGHT = 3


@dataclass
class TileEdgeData:
    """Data class for data stored on each tile edge. Many attributes are stored
    as pairs of data to correspond to the two corners of the tile edge. These
    corners are ordered clockwise around the tile (the tile should be on your
    right as you traverse from the first to second corner).
    """

    #: Should this edge produce collisions
    solid: bool = False
    #: Is this edge visible
    visible: bool = False
    #: Wether an edge cap should be drawn for each corner
    caps: Tuple[bool, bool] = (False, False)
    #: Edge join angle in degrees, should be in the range #: -90 < angle < 90.
    #: Ignored if the corresponding cap flag is set.
    angles: Tuple[int, int] = (0, 0)
    #: Sprite set of dust or spikes on this edge. Use `TileSpriteSet.NONE_0`
    #: to indicate no filth on this edge.
    filth_sprite_set: TileSpriteSet = TileSpriteSet.NONE_0
    #: If :attr:`filth_sprite_set` is not `TileSpriteSet.NONE_0` this flag
    #: controls if there is dust or spikes on the edge.
    filth_spike: bool = False
    #: Same as :attr:`caps` but for drawing filth (dust/spikes) caps.
    filth_caps: Tuple[bool, bool] = (False, False)
    #: Same as :attr:`angles` but for filth join angles.
    filth_angles: Tuple[int, int] = (0, 0)


class TileShape(IntEnum):
    """Tiles come in four main types; full, half, big, and small. Images of
    those tiles can be seen below. Alternatively refer to
    https://github.com/cmann1/PropUtils/blob/master/files/tiles_reference/TileShapes.jpg
    for an image of all tiles in one place.
    """

    #: .. image:: images/tiles/full.png
    FULL = 0
    #: .. image:: images/tiles/big_1.png
    BIG_1 = 1
    #: .. image:: images/tiles/small_1.png
    SMALL_1 = 2
    #: .. image:: images/tiles/big_2.png
    BIG_2 = 3
    #: .. image:: images/tiles/small_2.png
    SMALL_2 = 4
    #: .. image:: images/tiles/big_3.png
    BIG_3 = 5
    #: .. image:: images/tiles/small_3.png
    SMALL_3 = 6
    #: .. image:: images/tiles/big_4.png
    BIG_4 = 7
    #: .. image:: images/tiles/small_4.png
    SMALL_4 = 8
    #: .. image:: images/tiles/big_5.png
    BIG_5 = 9
    #: .. image:: images/tiles/small_5.png
    SMALL_5 = 10
    #: .. image:: images/tiles/big_6.png
    BIG_6 = 11
    #: .. image:: images/tiles/small_6.png
    SMALL_6 = 12
    #: .. image:: images/tiles/big_7.png
    BIG_7 = 13
    #: .. image:: images/tiles/small_7.png
    SMALL_7 = 14
    #: .. image:: images/tiles/big_8.png
    BIG_8 = 15
    #: .. image:: images/tiles/small_8.png
    SMALL_8 = 16
    #: .. image:: images/tiles/half_a.png
    HALF_A = 17
    #: .. image:: images/tiles/half_b.png
    HALF_B = 18
    #: .. image:: images/tiles/half_c.png
    HALF_C = 19
    #: .. image:: images/tiles/half_d.png
    HALF_D = 20


class Tile:
    """Represents a single tile in a Dustforce level. Positional information
    (x, y, layer) is stored within the containing :class:`Level` and not in
    the Tile object itself.

    Tiles support the equality and hashing interface.

    The constructor will by default create a square virtual tile with 4
    zeroed (non-solid nor visible) edges.

    Attributes:
        shape (TileShape): The shape of this particular tile.
        tile_flags (3-bit int): Raw bitmask of flags from the Dustforce engine.
            In practice this always seems to be 0x4 (which is set by default)
            corresponding to just the "solid" flag set. In most cases you should
            just ignore this flag. From the engine the definitions are:

            * Bit 1 - "solid slope flag" (probably ignored)
            * Bit 2 - "visible flag" (probably ignored)
            * Bit 3 - solid flag
        edge_data: List[TileEdgeData]: Edge data for each edge of the tile. This should always
            be a list of length 4 regardless of the tile :attr:`shape`.
        sprite_set (TileSpriteSet): The sprite set this tile comes from. (e.g.
            forest, mansion)
        sprite_tile (int): The index of the specific tile within this sprite set (e.g.
            grass, dirt). Check https://github.com/cmann1/PropUtils/tree/master/files/tiles_reference
            for a visual reference to get sprite index information.
        sprite_palette (int): The color variant of this tile.
    """

    def __init__(
        self,
        shape: TileShape = TileShape.FULL,
        *,
        tile_flags: int = 0x4,
        sprite_set: TileSpriteSet = TileSpriteSet.TUTORIAL,
        sprite_tile: int = 1,
        sprite_palette: int = 0,
        _tile_data: Optional[bytes] = None,
        _dust_data: Optional[bytes] = None,
    ) -> None:
        self.shape = shape
        self.tile_flags = tile_flags
        self.edge_data = [TileEdgeData() for _ in TileSide]
        self.sprite_set = sprite_set
        self.sprite_tile = sprite_tile
        self.sprite_palette = sprite_palette

        if _tile_data is not None:
            self._unpack_tile_data(_tile_data)
        if _dust_data is not None:
            self._unpack_dust_data(_dust_data)

    def __eq__(self, oth):
        if not isinstance(oth, Tile):
            return False
        return self._vals() == oth._vals()

    def __hash__(self):
        return hash(self._vals())

    def _vals(self):
        """Values used for __eq__ and __hash__"""
        return (
            self.shape,
            self.tile_flags,
            self.edge_data,
            self.sprite_set,
            self.sprite_tile,
            self.sprite_palette,
        )

    def get_sprite_tuple(self) -> Tuple[TileSpriteSet, int, int]:
        """Convenience method for getting a tuple that describes the sprite
        of a tile for easy sprite comparison and copying.

        Returns:
            A three-tuple containing the sprite set, tile, and palette of this tile.
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
        """Gives the path within the extracted sprite metadata to the tile sprite
        currently selected. You may retrieve the complete game sprites listing from
        https://www.dropbox.com/s/jm37ew9p74olgca/sprites.zip?dl=0
        """
        return "area/{}/tiles/tile{}_{}_0001.png".format(
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
        """Returns true if the tile is a dustblock tile. This is calculated
        based on the current sprite information."""
        return SPRITE_SET_DUSTBLOCK_TILE[self.sprite_set] == self.sprite_tile

    def set_dustblock(self) -> None:
        """Update :attr:`sprite_tile` and :attr:`sprite_palette` to be the dustblock matching
        the current :attr:`sprite_set`.

        Raises:
            ValueError: If there is no dustblock tile for the current sprite set.
        """
        sprite_tile = SPRITE_SET_DUSTBLOCK_TILE[self.sprite_set]
        if sprite_tile == -1:
            raise ValueError("current sprite set does not have a dustblock tile")
        self.sprite_tile = sprite_tile
        self.sprite_palette = 1

    def transform(self, mat: TxMatrix) -> None:
        """Performs a flip and rotation as dictated by the tranformation matrix.
        Does not do any kind of scaling or skewing beyond that. Use :meth:`upscale`
        if you want to increase tile scale.

        Attributes:
            mat: The transformation matrix. See :meth:`dustmaker.level.Level.transform`
        """
        oshape = self.shape
        flipped = mat.flipped
        if flipped:
            # horizontally flip
            if self.shape == TileShape.FULL:
                self.edge_data[TileSide.LEFT], self.edge_data[TileSide.RIGHT] = (
                    self.edge_data[TileSide.RIGHT],
                    self.edge_data[TileSide.LEFT],
                )
            elif self.shape <= TileShape.SMALL_8:
                # No need to fix edge data order as SHAPE_ORDERED_SIDES uniquely
                # maps the transformed sides to original sides.
                self.shape = TileShape(1 + ((self.shape - TileShape.BIG_1) ^ 8) % 16)
            else:
                # Flipping swaps clockwise direction so we do the same.
                s1 = SHAPE_ORDERED_SIDES[self.shape][1]
                s2 = SHAPE_ORDERED_SIDES[self.shape][2]
                self.edge_data[s1], self.edge_data[s2] = (
                    self.edge_data[s2],
                    self.edge_data[s1],
                )
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

        og_edge_data = [self.edge_data[side] for side in SHAPE_ORDERED_SIDES[oshape]]
        self.edge_data = [TileEdgeData() for _ in TileSide]

        for i, side in enumerate(SHAPE_ORDERED_SIDES[self.shape]):
            if self.shape == TileShape.FULL:
                i = (i - angle) & 3
            self.edge_data[side] = og_edge_data[i]

    def upscale(self, factor: int) -> Generator[Tuple[int, int, "Tile"], None, None]:
        """
        Upscales a tile, returning a list of (dx, dy, tile) tuples giving
        the relative position of the upscaled tiles and the new tile shape.
        This is primarily used by :meth:`dustmaker.level.Level.upscale`.

        Yields:
            A three tuple (dx, dy, ntile) where (dx, dy) are the relative position
            within the scaled up `factor` x `factor` tile square formed and
            `ntile` is the tile that belongs at that position.
        """
        if factor < 1:
            return
        if factor == 1:
            yield 0, 0, copy.deepcopy(self)
            return

        def _tuple_set(data: Tuple, ind: int, value) -> Tuple:
            return tuple((value if i == ind else x) for i, x in enumerate(data))

        def _copy_side(dx: int, dy: int, tile: Tile, side: TileSide):
            """Copies a side from self into the upscaled tile. Adjust the
            caps if the edge does not leave the upscaled tile boundary.
            """
            edge_data = copy.deepcopy(self.edge_data[side])

            cw_ind = SIDE_CLOCKWISE_INDEX[side]
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
            mat = TxMatrix.ROTATE[-rots % 4]
            imat = TxMatrix.ROTATE[rots % 4]

            # Apply horizontal flip
            if hflip:
                mat = mat * TxMatrix.HFLIP
                imat = TxMatrix.HFLIP * imat

            # Fix up offset so transformed positions stay in upscale square.
            mat = mat.translate(
                *(max(0, -val) for val in mat.sample(factor - 1, factor - 1))
            )
            imat = imat.translate(
                *(max(0, -val) for val in imat.sample(factor - 1, factor - 1))
            )

            # Copy tile and transform it.
            ntile = copy.deepcopy(self)
            ntile.transform(mat)  # type: ignore
            assert ntile.shape in (TileShape.HALF_A, TileShape.BIG_1, TileShape.SMALL_1)

            # For each of the new upscaled tiles inverse the transformation.
            for dx, dy, tile in ntile.upscale(factor):
                tile.transform(imat)  # type: ignore
                tx, ty = imat.sample(dx, dy)
                yield (int(tx), int(ty), tile)

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


#: Mapping of :class:`TileSpriteSet` to the corresponding dustblock index
#: for that sprite set. Gives -1 if no dustblock tile is available for the
#: given sprite set.
#:
#: Type:
#:     tuple mapping :class:`TileSpriteSet` -> int
#:
#: :meta hide-value:
SPRITE_SET_DUSTBLOCK_TILE = (
    -1,  # NONE_0
    21,  # MANSION
    13,  # FOREST
    6,  # CITY
    9,  # LABORATORY
    2,  # TUTORIAL
    -1,  # NEXUS
    -1,  # NONE_7
)


#: A mapping of :class:`TileShape` to a sequence of sides.
#:
#: For: :attr:`TileShape.FULL` this is ordered clockwise starting with
#: the top side.
#:
#: For half tiles and small slants the ordering starts on the diagonal
#: edge and procedes clockwise around the tile.
#:
#: For big slants the ordering starts on the diagonal, then the opposite
#: side, then the flat side that's not present on the small slants. For
#: BIG_1 through BIG_4 this is clockwise, for BIG_5 through BIG_8 this
#: is counter-clockwise.
#:
#: Type:
#:     tuple mapping :class:`TileShape` -> (TileSide, ...)
#:
#: :meta hide-value:
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


#: Mapping of :class:`TileShape` to the vertex coordinates of the tile in
#: half-tile units. Vertexes are listed top-left, top-right, bottom-right,
#: and bottom-left order.
#:
#: Type:
#:     tuple mapping :class:`TileShape` -> ((int, int), (int, int), (int, int), (int, int))
#:
#: :meta hide-value:
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


#: Mapping of :class:`TileSide` to the index of that tile side when sides are
#: listed in clockwise order. This is useful for computing the edge vertexes
#: for a given side from :attr:`SHAPE_VERTEXES`.
#:
#: Type:
#:     tuple mapping :class:`TileSide` -> int
#:
#: Examples:
#:     ::
#:
#:         shape, side = TileShape.BIG_1, TileSide.TOP
#:         ind = SIDE_CLOCKWISE_INDEX[side]
#:         vert_a = SHAPE_VERTEXES[shape][ind]
#:         vert_b = SHAPE_VERTEXES[shape][(ind + 1) % 4]
#:         # vert_a = (0, 0), vert_b = (2, 1)
#:
#: :meta hide-value:
SIDE_CLOCKWISE_INDEX = (
    0,  # TOP
    2,  # BOTTOM
    3,  # LEFT
    1,  # RIGHT
)
