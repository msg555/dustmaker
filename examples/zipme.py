from dustmaker import *

import random

""" Transforms water tiles on layer 19 with a water tile on layer 14 behind them
    into an up zip.
"""

f0 = "/home/msg555/Dustforce/content/levels2/downhill"
f1 = "/home/msg555/.HitboxTeam/Dustforce/user/level_src/test"

with open(f0, "rb") as f:
    map = read_map(f.read())


def isziptile(tile):
    """Returns true if the tile is a water tile."""
    return tile.sprite_set() == TileSpriteSet.mansion and tile.sprite_tile() == 20


# Loop over each tile looking for something that needs to become a zip.
for ((layer, x, y), tile) in map.tiles.items():
    if layer == 19 and isziptile(tile):
        nt = map.get_tile(14, x, y)
        if nt and isziptile(nt):
            # Make the zip tile only have a top wall so you can't enter from the
            # bottom and get pushed up through the top.
            tile.edge_bits(TileSide.TOP, 0xF)
            tile.edge_bits(TileSide.BOTTOM, 0x0)
            tile.edge_bits(TileSide.LEFT, 0x0)
            tile.edge_bits(TileSide.RIGHT, 0x0)

            # Make the tiles on the left and right have walls so you can't leave the
            # zip.
            lft = map.get_tile(layer, x - 1, y)
            rht = map.get_tile(layer, x + 1, y)
            if lft:
                lft.edge_bits(TileSide.RIGHT, 0xF)
            if rht:
                rht.edge_bits(TileSide.LEFT, 0xF)

with open(f1, "wb") as f:
    f.write(write_map(map))
