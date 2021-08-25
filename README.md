Dustmaker
=========

Dustmaker is a Python library for reading, manipulation, and writing
binary files used by Dustforce, primarily level files.

Documentation
-------------

Documentation can be found at
[https://dustmaker.readthedocs.io/en/latest/](https://dustmaker.readthedocs.io/en/latest/).

Installation
------------

    easy_install3 dustmaker

or

    python3 -m pip install dustmaker

Example: Creating a new level from scratch
---------------------------

```python
from dustmaker.level import Level
from dustmaker.tile import Tile, TileShape
from dustmaker.dfwriter import DFWriter

# Create a new empty level and add some tiles.
level = Level()
level.name = b"my level!"
level.virtual_character = True
for i, shape in enumerate(TileShape):
    level.tiles[(19, 2 * i, i)] = Tile(shape)

# Automatically figure out edge solidity and connectivity flags
level.calculate_edge_visibility()
level.calculate_edge_caps()

# Write level to a file
with DFWriter(open("mylevel.dflevel", "wb")) as writer:
    writer.write_level(level)
```

Example: Counting how many apples are in a level
--------------------------

```python
from dustmaker.dfreader import DFReader
from dustmaker.entity import Apple

with DFReader(open("mylevel.dflevel", "rb")) as reader:
    level = reader.read_level()

apples = 0
for x, y, entity in level.entities.values():
    if isinstance(entity, Apple):
        apples += 1

print(f"Level has {apples} apples")
```
