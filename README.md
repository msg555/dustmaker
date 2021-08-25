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

Install with pip through PyPi using

    python -m pip install dustmaker

or clone this repository and install using

    ./setup.py install

Command Line Tool
---------------------------

Dustmaker comes with a few command line tools that can be accessed through
running the dustmaker module.

```bash
$ python -m dustmaker --help
... listing of available utilities
$ python -m dustmaker transform --upscale 2 downhill big_downhill
... creates upscaled version of downhill and saves to "big_downhill"
```

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
