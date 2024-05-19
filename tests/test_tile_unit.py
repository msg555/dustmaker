"""
Unit tests for tile module routines
"""

import copy
import itertools
import random
import unittest
from typing import Dict

from dustmaker.tile import Tile, TileEdgeData, TileShape, TileSide, TileSpriteSet
from dustmaker.transform import TxMatrix


def rand_edge(rng: random.Random) -> TileEdgeData:
    """Generate random edge data"""
    abool = (False, True)
    return TileEdgeData(
        solid=rng.choice(abool),
        visible=rng.choice(abool),
        caps=tuple(rng.choices(abool, k=2)),
        angles=(rng.randint(-127, 127), rng.randint(-127, 127)),
        filth_caps=tuple(rng.choices(abool, k=2)),
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

    def _assert_match(
        self, tile: Tile, ntile: Tile, shape: TileShape, edge_caps: Dict[TileSide, int]
    ) -> None:
        """Check that ntile is of the expected shape and copies the expected
        edges and caps from tile.
        """
        self.assertEqual(shape, ntile.shape)

        null_edge = TileEdgeData()
        for side in TileSide:
            cap_dr = edge_caps.get(side)
            nedge_data = ntile.edge_data[side]
            if cap_dr is None:
                self.assertEqual(null_edge, nedge_data)
                continue

            edge_data = tile.edge_data[side]
            self.assertEqual(edge_data.solid, nedge_data.solid)
            self.assertEqual(edge_data.visible, nedge_data.visible)
            self.assertEqual(edge_data.filth_sprite_set, nedge_data.filth_sprite_set)
            self.assertEqual(edge_data.filth_spike, nedge_data.filth_spike)

            for dr in range(2):
                if dr == cap_dr:
                    self.assertEqual(edge_data.caps[dr], nedge_data.caps[dr])
                    self.assertEqual(edge_data.angles[dr], nedge_data.angles[dr])
                    self.assertEqual(
                        edge_data.filth_caps[dr], nedge_data.filth_caps[dr]
                    )
                    self.assertEqual(
                        edge_data.filth_angles[dr], nedge_data.filth_angles[dr]
                    )
                else:
                    self.assertFalse(nedge_data.caps[dr])
                    self.assertEqual(0, nedge_data.angles[dr])
                    self.assertFalse(nedge_data.filth_caps[dr])
                    self.assertEqual(0, nedge_data.filth_angles[dr])

    @seeded_rand
    def test_upscale_full(self, rng: random.Random):
        """full upscale"""
        tile = rand_tile(rng, TileShape.FULL)

        # Base check factor < 1
        upscale_list = list(tile.upscale(0))
        self.assertFalse(upscale_list)

        # Base check factor == 1
        upscale_list = list(tile.upscale(1))
        self.assertEqual((0, 0, tile), upscale_list[0])
        self.assertIsNot(tile, upscale_list[0][2])

        # factor == 2
        upscale_list = list(tile.upscale(2))
        self.assertEqual(4, len(upscale_list))
        tile_map = {(dx, dy): ntile for dx, dy, ntile in upscale_list}

        self._assert_match(
            tile, tile_map[(0, 0)], TileShape.FULL, {TileSide.LEFT: 1, TileSide.TOP: 0}
        )
        self._assert_match(
            tile, tile_map[(1, 0)], TileShape.FULL, {TileSide.RIGHT: 0, TileSide.TOP: 1}
        )
        self._assert_match(
            tile,
            tile_map[(1, 1)],
            TileShape.FULL,
            {TileSide.RIGHT: 1, TileSide.BOTTOM: 0},
        )
        self._assert_match(
            tile,
            tile_map[(0, 1)],
            TileShape.FULL,
            {TileSide.LEFT: 0, TileSide.BOTTOM: 1},
        )

        # factor == 3
        upscale_list = list(tile.upscale(3))
        self.assertEqual(9, len(upscale_list))
        tile_map = {(dx, dy): ntile for dx, dy, ntile in upscale_list}

        self._assert_match(
            tile, tile_map[(0, 0)], TileShape.FULL, {TileSide.LEFT: 1, TileSide.TOP: 0}
        )
        self._assert_match(tile, tile_map[(1, 0)], TileShape.FULL, {TileSide.TOP: -1})
        self._assert_match(
            tile, tile_map[(2, 0)], TileShape.FULL, {TileSide.RIGHT: 0, TileSide.TOP: 1}
        )
        self._assert_match(tile, tile_map[(2, 1)], TileShape.FULL, {TileSide.RIGHT: -1})
        self._assert_match(
            tile,
            tile_map[(2, 2)],
            TileShape.FULL,
            {TileSide.RIGHT: 1, TileSide.BOTTOM: 0},
        )
        self._assert_match(
            tile, tile_map[(1, 2)], TileShape.FULL, {TileSide.BOTTOM: -1}
        )
        self._assert_match(
            tile,
            tile_map[(0, 2)],
            TileShape.FULL,
            {TileSide.LEFT: 0, TileSide.BOTTOM: 1},
        )
        self._assert_match(tile, tile_map[(0, 1)], TileShape.FULL, {TileSide.LEFT: -1})
        self._assert_match(tile, tile_map[(1, 1)], TileShape.FULL, {})

    @seeded_rand
    def test_upscale_half(self, rng: random.Random):
        """half upscale"""
        tile = rand_tile(rng, TileShape.HALF_A)

        for factor, rot in itertools.product((2, 3), range(4)):
            ntile = copy.deepcopy(tile)
            ntile.transform(TxMatrix.ROTATE[-rot % 4])
            upscale_list = list(ntile.upscale(factor))

            ox, oy = TxMatrix.ROTATE[rot].sample(factor - 1, factor - 1)
            for i, (dx, dy, ntile) in enumerate(upscale_list):
                tx, ty = TxMatrix.ROTATE[rot].sample(dx, dy)
                ntile.transform(TxMatrix.ROTATE[rot])
                upscale_list[i] = (tx + max(0, -ox), ty + max(0, -oy), ntile)
            tile_map = {(dx, dy): ntile for dx, dy, ntile in upscale_list}

            if factor == 2:
                self.assertEqual(3, len(upscale_list))
                self._assert_match(
                    tile,
                    tile_map[(0, 0)],
                    TileShape.HALF_A,
                    {TileSide.LEFT: 1, TileSide.TOP: 0},
                )
                self._assert_match(
                    tile,
                    tile_map[(1, 1)],
                    TileShape.HALF_A,
                    {TileSide.TOP: 1, TileSide.BOTTOM: 0},
                )
                self._assert_match(
                    tile,
                    tile_map[(0, 1)],
                    TileShape.FULL,
                    {TileSide.LEFT: 0, TileSide.BOTTOM: 1},
                )
            else:
                self.assertEqual(6, len(upscale_list))
                self._assert_match(
                    tile,
                    tile_map[(0, 0)],
                    TileShape.HALF_A,
                    {TileSide.LEFT: 1, TileSide.TOP: 0},
                )
                self._assert_match(
                    tile, tile_map[(1, 1)], TileShape.HALF_A, {TileSide.TOP: -1}
                )
                self._assert_match(
                    tile,
                    tile_map[(2, 2)],
                    TileShape.HALF_A,
                    {TileSide.BOTTOM: 0, TileSide.TOP: 1},
                )
                self._assert_match(
                    tile, tile_map[(1, 2)], TileShape.FULL, {TileSide.BOTTOM: -1}
                )
                self._assert_match(
                    tile,
                    tile_map[(0, 2)],
                    TileShape.FULL,
                    {TileSide.LEFT: 0, TileSide.BOTTOM: 1},
                )
                self._assert_match(
                    tile, tile_map[(0, 1)], TileShape.FULL, {TileSide.LEFT: -1}
                )

    @seeded_rand
    def test_upscale_big(self, rng: random.Random):
        """big upscale"""
        tile = rand_tile(rng, TileShape.BIG_1)

        for flip, factor, rot in itertools.product((True, False), (2, 3), range(4)):
            mat = (TxMatrix.HFLIP if flip else TxMatrix.IDENTITY) * TxMatrix.ROTATE[rot]
            imat = TxMatrix.ROTATE[-rot % 4] * (
                TxMatrix.HFLIP if flip else TxMatrix.IDENTITY
            )

            ntile = copy.deepcopy(tile)
            ntile.transform(mat)
            upscale_list = list(ntile.upscale(factor))

            ox, oy = imat.sample(factor - 1, factor - 1)
            for i, (dx, dy, ntile) in enumerate(upscale_list):
                tx, ty = imat.sample(dx, dy)
                ntile.transform(imat)
                upscale_list[i] = (tx + max(0, -ox), ty + max(0, -oy), ntile)
            tile_map = {(dx, dy): ntile for dx, dy, ntile in upscale_list}

            if factor == 2:
                self.assertEqual(4, len(upscale_list))
                self._assert_match(
                    tile,
                    tile_map[(0, 0)],
                    TileShape.BIG_1,
                    {TileSide.LEFT: 1, TileSide.TOP: 0},
                )
                self._assert_match(
                    tile, tile_map[(1, 0)], TileShape.SMALL_1, {TileSide.TOP: 1}
                )
                self._assert_match(
                    tile, tile_map[(1, 1)], TileShape.FULL, {TileSide.BOTTOM: 0}
                )
                self._assert_match(
                    tile,
                    tile_map[(0, 1)],
                    TileShape.FULL,
                    {TileSide.LEFT: 0, TileSide.BOTTOM: 1},
                )
            else:
                self.assertEqual(8, len(upscale_list))
                self._assert_match(
                    tile,
                    tile_map[(0, 0)],
                    TileShape.BIG_1,
                    {TileSide.LEFT: 1, TileSide.TOP: 0},
                )
                self._assert_match(
                    tile, tile_map[(1, 0)], TileShape.SMALL_1, {TileSide.TOP: -1}
                )
                self._assert_match(
                    tile, tile_map[(2, 1)], TileShape.BIG_1, {TileSide.TOP: 1}
                )
                self._assert_match(
                    tile, tile_map[(2, 2)], TileShape.FULL, {TileSide.BOTTOM: 0}
                )
                self._assert_match(
                    tile, tile_map[(1, 2)], TileShape.FULL, {TileSide.BOTTOM: -1}
                )
                self._assert_match(
                    tile,
                    tile_map[(0, 2)],
                    TileShape.FULL,
                    {TileSide.LEFT: 0, TileSide.BOTTOM: 1},
                )
                self._assert_match(
                    tile, tile_map[(0, 1)], TileShape.FULL, {TileSide.LEFT: -1}
                )
                self._assert_match(tile, tile_map[(1, 1)], TileShape.FULL, {})

    @seeded_rand
    def test_upscale_small(self, rng: random.Random):
        """small upscale"""
        tile = rand_tile(rng, TileShape.SMALL_1)

        for flip, factor, rot in itertools.product((True, False), (2, 3), range(4)):
            mat = (TxMatrix.HFLIP if flip else TxMatrix.IDENTITY) * TxMatrix.ROTATE[rot]
            imat = TxMatrix.ROTATE[-rot % 4] * (
                TxMatrix.HFLIP if flip else TxMatrix.IDENTITY
            )

            ntile = copy.deepcopy(tile)
            ntile.transform(mat)
            upscale_list = list(ntile.upscale(factor))

            ox, oy = imat.sample(factor - 1, factor - 1)
            for i, (dx, dy, ntile) in enumerate(upscale_list):
                tx, ty = imat.sample(dx, dy)
                ntile.transform(imat)
                upscale_list[i] = (tx + max(0, -ox), ty + max(0, -oy), ntile)
            tile_map = {(dx, dy): ntile for dx, dy, ntile in upscale_list}

            if factor == 2:
                self.assertEqual(2, len(upscale_list))
                self._assert_match(
                    tile,
                    tile_map[(0, 1)],
                    TileShape.BIG_1,
                    {TileSide.TOP: 0, TileSide.BOTTOM: 1},
                )
                self._assert_match(
                    tile,
                    tile_map[(1, 1)],
                    TileShape.SMALL_1,
                    {TileSide.TOP: 1, TileSide.BOTTOM: 0},
                )
            else:
                self.assertEqual(4, len(upscale_list))
                self._assert_match(
                    tile,
                    tile_map[(0, 1)],
                    TileShape.SMALL_1,
                    {TileSide.TOP: 0},
                )
                self._assert_match(
                    tile,
                    tile_map[(1, 2)],
                    TileShape.BIG_1,
                    {TileSide.TOP: -1, TileSide.BOTTOM: -1},
                )
                self._assert_match(
                    tile,
                    tile_map[(2, 2)],
                    TileShape.SMALL_1,
                    {TileSide.TOP: 1, TileSide.BOTTOM: 0},
                )
                self._assert_match(
                    tile,
                    tile_map[(0, 2)],
                    TileShape.FULL,
                    {TileSide.BOTTOM: 1},
                )
