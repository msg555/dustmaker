"""
Unit tests for tile module routines
"""
import copy
import random
from typing import Dict
import unittest

from dustmaker.tile import (
    Tile,
    TileEdgeData,
    TileShape,
    TileSide,
    TileSpriteSet,
)
from dustmaker.transform import TxMatrix


def rand_edge(rng: random.Random) -> TileEdgeData:
    """Generate random edge data"""
    abool = (False, True)
    return TileEdgeData(
        solid=rng.choice(abool),
        visible=rng.choice(abool),
        caps=rng.choices(abool, k=2),
        angles=(rng.randint(-127, 127), rng.randint(-127, 127)),
        filth_caps=rng.choices(abool, k=2),
        filth_angles=(rng.randint(-127, 127), rng.randint(-127, 127)),
    )


def rand_tile(rng: random.Random, shape: TileShape) -> Tile:
    """Generate a random tile of the given shape"""
    tile = Tile(shape)
    tile.sprite_set = rng.choice(list(TileSpriteSet))
    tile.sprite_tile = rng.randint(1, 20)
    tile.sprite_palette = rng.randint(1, 20)
    for side in TileSide:
        tile.edge_data[side] = rand_edge(rng)
    return tile


def seeded_rand(func):
    """Test decorator that passes a rng seeded on the test name"""

    def _invoke(*args, **kwargs):
        return func(*args, random.Random(func.__name__), **kwargs)

    return _invoke


class TestTileUnit(unittest.TestCase):
    """
    Unit tests for the tile module
    """

    def _assert_edge(self, flipped: bool, t1: TileEdgeData, t2: TileEdgeData):
        """Verify two edges are the same"""
        self.assertEqual(t1.solid, t2.solid)
        self.assertEqual(t1.visible, t2.visible)
        if flipped:
            self.assertEqual(t1.caps, t2.caps[::-1])
            self.assertEqual(t1.angles, (-t2.angles[1], -t2.angles[0]))
            self.assertEqual(t1.filth_caps, t2.filth_caps[::-1])
            self.assertEqual(
                t1.filth_angles, (-t2.filth_angles[1], -t2.filth_angles[0])
            )
        else:
            self.assertEqual(t1.caps, t2.caps)
            self.assertEqual(t1.angles, t2.angles)
            self.assertEqual(t1.filth_caps, t2.filth_caps)
            self.assertEqual(t1.filth_angles, t2.filth_angles)

    def _test_tx(
        self,
        rng: random.Random,
        shape: TileShape,
        nshape: TileShape,
        mat: TxMatrix,
        imat: TxMatrix,
        edge_map: Dict[TileSide, TileSide],
    ) -> None:
        """Test that a transformation produces expected results and that
        reverse transformation gets us back to the original tile.
        """
        tile = rand_tile(rng, shape)

        # Transform forward and make sure we get expected results.
        rtile = copy.deepcopy(tile)
        rtile.transform(mat)
        self.assertEqual(nshape, rtile.shape)
        self.assertEqual(tile.get_sprite_tuple(), rtile.get_sprite_tuple())

        flipped = mat.flipped
        for side, rside in edge_map.items():
            self._assert_edge(flipped, tile.edge_data[side], rtile.edge_data[rside])

        # Transform backward and make sure we get back where we started.
        rtile.transform(imat)
        self.assertEqual(shape, rtile.shape)
        self.assertEqual(tile.get_sprite_tuple(), rtile.get_sprite_tuple())
        for side in edge_map:
            self._assert_edge(False, tile.edge_data[side], rtile.edge_data[side])

    @seeded_rand
    def test_transform_full_rot(self, rng: random.Random):
        """full rot"""
        self._test_tx(
            rng,
            TileShape.FULL,
            TileShape.FULL,
            TxMatrix.ROTATE[1],
            TxMatrix.ROTATE[3],
            {
                TileSide.TOP: TileSide.RIGHT,
                TileSide.RIGHT: TileSide.BOTTOM,
                TileSide.BOTTOM: TileSide.LEFT,
                TileSide.LEFT: TileSide.TOP,
            },
        )

    @seeded_rand
    def test_transform_full_hflip(self, rng: random.Random):
        """full hflip"""
        self._test_tx(
            rng,
            TileShape.FULL,
            TileShape.FULL,
            TxMatrix.HFLIP,
            TxMatrix.HFLIP,
            {
                TileSide.TOP: TileSide.TOP,
                TileSide.BOTTOM: TileSide.BOTTOM,
                TileSide.LEFT: TileSide.RIGHT,
                TileSide.RIGHT: TileSide.LEFT,
            },
        )

    @seeded_rand
    def test_transform_full_vflip(self, rng: random.Random):
        """full vflip"""
        self._test_tx(
            rng,
            TileShape.FULL,
            TileShape.FULL,
            TxMatrix.VFLIP,
            TxMatrix.VFLIP,
            {
                TileSide.TOP: TileSide.BOTTOM,
                TileSide.BOTTOM: TileSide.TOP,
                TileSide.LEFT: TileSide.LEFT,
                TileSide.RIGHT: TileSide.RIGHT,
            },
        )

    @seeded_rand
    def test_transform_half_rot(self, rng: random.Random):
        """half rot"""
        self._test_tx(
            rng,
            TileShape.HALF_A,
            TileShape.HALF_B,
            TxMatrix.ROTATE[1],
            TxMatrix.ROTATE[3],
            {
                TileSide.TOP: TileSide.BOTTOM,
                TileSide.BOTTOM: TileSide.LEFT,
                TileSide.LEFT: TileSide.TOP,
            },
        )
        self._test_tx(
            rng,
            TileShape.HALF_C,
            TileShape.HALF_D,
            TxMatrix.ROTATE[1],
            TxMatrix.ROTATE[3],
            {
                TileSide.TOP: TileSide.RIGHT,
                TileSide.RIGHT: TileSide.BOTTOM,
                TileSide.BOTTOM: TileSide.TOP,
            },
        )

    @seeded_rand
    def test_transform_half_hflip(self, rng: random.Random):
        """half hflip"""
        self._test_tx(
            rng,
            TileShape.HALF_A,
            TileShape.HALF_D,
            TxMatrix.HFLIP,
            TxMatrix.HFLIP,
            {
                TileSide.TOP: TileSide.TOP,
                TileSide.BOTTOM: TileSide.BOTTOM,
                TileSide.LEFT: TileSide.RIGHT,
            },
        )
        self._test_tx(
            rng,
            TileShape.HALF_B,
            TileShape.HALF_C,
            TxMatrix.HFLIP,
            TxMatrix.HFLIP,
            {
                TileSide.TOP: TileSide.TOP,
                TileSide.BOTTOM: TileSide.BOTTOM,
                TileSide.LEFT: TileSide.RIGHT,
            },
        )

    @seeded_rand
    def test_transform_half_vflip(self, rng: random.Random):
        """half vflip"""
        self._test_tx(
            rng,
            TileShape.HALF_A,
            TileShape.HALF_B,
            TxMatrix.VFLIP,
            TxMatrix.VFLIP,
            {
                TileSide.TOP: TileSide.BOTTOM,
                TileSide.BOTTOM: TileSide.TOP,
                TileSide.LEFT: TileSide.LEFT,
            },
        )
        self._test_tx(
            rng,
            TileShape.HALF_C,
            TileShape.HALF_D,
            TxMatrix.VFLIP,
            TxMatrix.VFLIP,
            {
                TileSide.TOP: TileSide.BOTTOM,
                TileSide.BOTTOM: TileSide.TOP,
                TileSide.RIGHT: TileSide.RIGHT,
            },
        )

    @seeded_rand
    def test_transform_big_rot(self, rng: random.Random):
        """big rot"""
        self._test_tx(
            rng,
            TileShape.BIG_1,
            TileShape.BIG_2,
            TxMatrix.ROTATE[1],
            TxMatrix.ROTATE[3],
            {
                TileSide.TOP: TileSide.RIGHT,
                TileSide.BOTTOM: TileSide.LEFT,
                TileSide.LEFT: TileSide.TOP,
            },
        )
        self._test_tx(
            rng,
            TileShape.BIG_6,
            TileShape.BIG_5,
            TxMatrix.ROTATE[1],
            TxMatrix.ROTATE[3],
            {
                TileSide.RIGHT: TileSide.BOTTOM,
                TileSide.LEFT: TileSide.TOP,
                TileSide.TOP: TileSide.RIGHT,
            },
        )

    @seeded_rand
    def test_transform_big_hflip(self, rng: random.Random):
        """big hflip"""
        self._test_tx(
            rng,
            TileShape.BIG_1,
            TileShape.BIG_5,
            TxMatrix.HFLIP,
            TxMatrix.HFLIP,
            {
                TileSide.TOP: TileSide.TOP,
                TileSide.BOTTOM: TileSide.BOTTOM,
                TileSide.LEFT: TileSide.RIGHT,
            },
        )
        self._test_tx(
            rng,
            TileShape.BIG_2,
            TileShape.BIG_6,
            TxMatrix.HFLIP,
            TxMatrix.HFLIP,
            {
                TileSide.TOP: TileSide.TOP,
                TileSide.RIGHT: TileSide.LEFT,
                TileSide.LEFT: TileSide.RIGHT,
            },
        )

    @seeded_rand
    def test_transform_big_vflip(self, rng: random.Random):
        """big vflip"""
        self._test_tx(
            rng,
            TileShape.BIG_1,
            TileShape.BIG_7,
            TxMatrix.VFLIP,
            TxMatrix.VFLIP,
            {
                TileSide.TOP: TileSide.BOTTOM,
                TileSide.BOTTOM: TileSide.TOP,
                TileSide.LEFT: TileSide.LEFT,
            },
        )
        self._test_tx(
            rng,
            TileShape.BIG_2,
            TileShape.BIG_8,
            TxMatrix.VFLIP,
            TxMatrix.VFLIP,
            {
                TileSide.TOP: TileSide.BOTTOM,
                TileSide.RIGHT: TileSide.RIGHT,
                TileSide.LEFT: TileSide.LEFT,
            },
        )

    @seeded_rand
    def test_transform_small_rot(self, rng: random.Random):
        """small rot"""
        self._test_tx(
            rng,
            TileShape.SMALL_1,
            TileShape.SMALL_2,
            TxMatrix.ROTATE[1],
            TxMatrix.ROTATE[3],
            {TileSide.TOP: TileSide.RIGHT, TileSide.BOTTOM: TileSide.LEFT},
        )
        self._test_tx(
            rng,
            TileShape.SMALL_6,
            TileShape.SMALL_5,
            TxMatrix.ROTATE[1],
            TxMatrix.ROTATE[3],
            {TileSide.RIGHT: TileSide.BOTTOM, TileSide.LEFT: TileSide.TOP},
        )

    @seeded_rand
    def test_transform_small_hflip(self, rng: random.Random):
        """small hflip"""
        self._test_tx(
            rng,
            TileShape.SMALL_1,
            TileShape.SMALL_5,
            TxMatrix.HFLIP,
            TxMatrix.HFLIP,
            {TileSide.TOP: TileSide.TOP, TileSide.BOTTOM: TileSide.BOTTOM},
        )
        self._test_tx(
            rng,
            TileShape.SMALL_2,
            TileShape.SMALL_6,
            TxMatrix.HFLIP,
            TxMatrix.HFLIP,
            {TileSide.RIGHT: TileSide.LEFT, TileSide.LEFT: TileSide.RIGHT},
        )

    @seeded_rand
    def test_transform_small_vflip(self, rng: random.Random):
        """small vflip"""
        self._test_tx(
            rng,
            TileShape.SMALL_1,
            TileShape.SMALL_7,
            TxMatrix.VFLIP,
            TxMatrix.VFLIP,
            {TileSide.TOP: TileSide.BOTTOM, TileSide.BOTTOM: TileSide.TOP},
        )
        self._test_tx(
            rng,
            TileShape.SMALL_2,
            TileShape.SMALL_8,
            TxMatrix.VFLIP,
            TxMatrix.VFLIP,
            {TileSide.RIGHT: TileSide.RIGHT, TileSide.LEFT: TileSide.LEFT},
        )
