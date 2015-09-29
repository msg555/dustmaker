Dustmaker
=========

Documentation
-------------

[http://dustkid.com/static/dustmaker/index.html](http://dustkid.com/static/dustmaker/index.html)

Installation
------------

    easy_install3 dustmaker

or

    pip install dustmaker

Creating A Map From Scratch
---------------------------

    from dustmaker import write_map, Map, Tile, TileShape

    map = Map()
    map.start_position((0, 0))
    map.virtual_character(True)
    for (i, shape) in enumerate(TileShape):
      map.add_tile(19, 2 * i, 1, Tile(shape))
    map.name("Test Map")

    f_out = "/home/msg555/.HitboxTeam/Dustforce/user/level_src/testmap"

    with open(f_out, "wb") as f:
      f.write(write_map(map))


Reading in an existing map
--------------------------

    from dustmaker import read_map

    f_in = "/home/msg555/Dustforce/content/levels2/downhill"
    with open(f_in, "rb") as f:
      map = read_map(f.read())
