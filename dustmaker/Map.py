from .MapException import MapException
from .Var import Var, VarType
from .Tile import TileSide, tile_maximal_bits
from .LevelType import LevelType

import copy

class Map:
  """ Represents a Dustforce level.

      A map contains the following attributes:

      map.tiles - A dict mapping (layer, x, y) to Tile objects.
      map.props - A dict mapping prop ids to Prop objects.
      map.parent - For backdrops this is the containing map.  Otherwise this is
                   set to None.

      If the map is not a backdrop (i.e. map.parent == None) then the following
      attributes will also be available:

      map.entities - A dict mapping entity ids to Entity objects.
      map.backdrop - The backdrop Map object.  Backdrop maps can only contain
                     tiles and props and each tile is the size of 16 tiles in
                     the top level coordinate system.
      map.vars - A raw mapping of string keys to Var objects.  Some of these
                 variables have nicer accessors like map.name(...).
      map.sshot - The level thumbnail image.  This appears to be a PNG image
                   with some custom or missing header.
  """

  def __init__(self, parent = None):
    """ Constructs a blank level object.

        parent - If this Map represents a backdrop this is the containing map.
                 Typical usage should not need to use this parameter.
    """
    self._min_id = 100
    self.tiles = {}
    self.props = {}
    self.vars = {}

    self.parent = parent
    if not parent:
      self.sshot = b""
      self.entities = {}
      self.backdrop = Map(self)

    self.dustmod_version("dustmaker")

  def _next_id(self):
    if self.parent:
      return self.parent._next_id()
    result = self._min_id
    self._min_id += 1
    return result

  def _note_id(self, id):
    if self.parent:
      return self.parent._note_id(id)
    self._min_id = max(self._min_id, id + 1)

  def _var_access(self, key, type, val = None, default = None):
    result = default
    if key in self.vars:
      result = self.vars[key].value
    if not val is None:
      self.vars[key] = Var(type, val)
    return result

  def name(self, val = None):
    """ Returns the level name.

        val - If not None sets the new name of the Map.
    """
    return self._var_access("level_name", VarType.STRING, val, "")

  def start_position(self, val = None, player = 1):
    """ Returns the starting position of a player as a tuple of floats.

        val - If not None sets the new player position.
        player - The player ID to set the position of.
    """
    result = [0, 0]
    keys = ["p%d_x" % player, "p%d_y" % player]
    for (i, key) in enumerate(keys):
      if key in self.vars:
        result[i] = self.vars[key].value / 48.0
      if not val is None:
        self.vars[key] = Var(VarType.UINT, int(round(val[i] * 48)))
    return (result[0], result[1])

  def virtual_character(self, val = None):
    """ Returns True if the map uses virtual characters.

        val - If not None sets the virtual character flag for the map.
    """
    return self._var_access("vector_character", VarType.BOOL, val, False)

  def level_type(self, val = None):
    """ Returns the type of the level (e.g., Normal, Nexus, etc.).

        val - If not None sets the level type. Use the LevelType enum.
    """
    return self._var_access("level_type", VarType.UINT, val, 0)

  def dustmod_version(self, val = None):
    """ Returns the dustmod version used to create this map.
    """
    """ val - If not None sets the level dustmod version.
    """
    return self._var_access("dustmod_version", VarType.STRING, val, "")

  def add_entity(self, x, y, entity, id = None):
    """ Adds a new entity to the map and returns its id.

        x - The x position in tile units of the entity.
        y - The y position in tile units of the entity.
        entity - The Entity object to add to the map.
        id - The entity identifier.  If set to None the identifier will be
             allocated for you.

        Raises a MapException if the given id is already in use.
    """
    if id is None or id in self.entities:
      id = self._next_id()
    else:
      self._note_id(id)
    if id in self.entities:
      raise MapException("map already has id")
    self.entities[id] = (x, y, entity)
    return id

  def add_prop(self, layer, x, y, prop, id = None):
    """ Adds a new prop to the map and returns its id.

        x - The x position in tile units of the prop.
        y - The y position in tile units of the prop.
        prop - The Prop object to add to the map.
        id - The prop identifier.  If set to None the identifier will be
             allocated for you.

        Raises a MapException if the given id is already in use.
    """
    if id is None or id in self.props:
      id = self._next_id()
    else:
      self._note_id(id)
    if id in self.props:
      raise MapException("map already has prop id")
    self.props[id] = (layer, x, y, prop)
    return id

  def add_tile(self, layer, x, y, tile):
    """ Adds a new tile to the map.

        layer - The layer to add the tile.
        x - The x position of the tile.
        y - The y position of the tile.
        tile - The tile to add to the map.

        Raises a MapException if the given position is already occupied.
    """
    if (layer, x, y) in self.tiles:
      raise MapException("tile already exists")
    self.tiles[(layer, x, y)] = tile

  def set_tile(self, layer, x, y, tile):
    """ Like add_tile but overwrites any existing tile.
    """
    self.tiles[(layer, x, y)] = tile

  def get_tile(self, layer, x, y):
    """ Returns the tile at the given position or None.

        layer - The layer to add the tile.
        x - The x position of the tile.
        y - The y position of the tile.
    """
    return self.tiles.get((layer, x, y), None)

  def delete_tile(self, layer, x, y):
    """ Delete the tile at the given position if present.

        layer - The layer to add the tile.
        x - The x position of the tile.
        y - The y position of the tile.
    """
    if (layer, x, y) in self.tiles:
      del self.tiles[(layer, x, y)]

  def get_prop(self, id):
    """ Returns the Prop object with the given id or None. """
    return self.props.get(id, (None, None, None, None))[3]

  def get_prop_layer(self, id):
    """ Returns the layer of the prop with the given id or None. """
    return self.props.get(id, (None, None, None, None))[0]

  def get_prop_xposition(self, id):
    """ Returns the x position of the prop with the given id or None. """
    return self.props.get(id, (None, None, None, None))[1]

  def get_prop_yposition(self, id):
    """ Returns the y position of the prop with the given id or None. """
    return self.props.get(id, (None, None, None, None))[2]

  def get_entity(self, id):
    """ Returns the Entity object with the given id or None. """
    return self.entities.get(id, (None, None, None))[2]

  def get_entity_xposition(self, id):
    """ Returns the x position of the entity with the given id or None. """
    return self.entities.get(id, (None, None, None))[0]

  def get_entity_yposition(self, id):
    """ Returns the y position of the entity with the given id or None. """
    return self.entities.get(id, (None, None, None))[1]

  def translate(self, x, y):
    """ Translate the entire map x tiles laterally and y tiles horizontally.

        x - The number of tiles to move laterally.  If a float tiles will be
            moved by the nearest integer.
        y - The number of tiles to move horizontally.  If a float tiles will be
            moved by the nearest integer.
    """
    self.transform([[1, 0, x], [0, 1, y], [0, 0, 1]])

  def remap_ids(self, min_id = None):
    """ Remap prop and entity ids starting at min_id.

        This calls through to all entities to remap any references to other
        entity ids.
    """
    if min_id is None:
      self._min_id = 100
    else:
      self._min_id = min_id

    prop_remap = {}
    for id in self.props.keys():
      prop_remap[id] = self._next_id()
    self.props = {prop_remap[id]: self.props[id] for
                       id in self.props.keys()}

    if hasattr(self, "backdrop"):
      entity_remap = {}
      for id in self.entities.keys():
        entity_remap[id] = self._next_id()
      self.entities = {entity_remap[id]: self.entities[id] for
                         id in self.entities.keys()}
      for (x, y, entity) in self.entities.values():
        entity.remap_ids(entity_remap)

      self.backdrop.remap_ids()

  def merge_map(self, map, _do_remap_ids = True):
    """ Merge a map into this one.

        map - The Map to merge into this one.
    """
    if _do_remap_ids:
      self.remap_ids(map._min_id)
    self.tiles.update(copy.deepcopy(map.tiles))
    self.props.update(copy.deepcopy(map.props))

    if hasattr(self, "backdrop") and hasattr(map, "backdrop"):
      self.entities.update(copy.deepcopy(map.entities))
      self.backdrop.merge_map(map.backdrop, False)

  def transform(self, mat):
    """ Transforms the map with the given affine transformation matrix.  Note
        that this will probably not produce desirable results if the
        transformation matrix is not some mixture of a translation, flip,
        and 90 degree rotations.

        In most cases you should not use this method directly and instead use
        Map.flip_horizontal(), Map.flip_vertical(), or Map.rotate().

        mat - The affine transformation matrix. [x', y', 1]' = mat * [x, y, 1]'
    """
    self.tiles = {(layer, mat[0][2] + x * mat[0][0] + y * mat[0][1] +
                          min(0, mat[0][0]) + min(0, mat[0][1]),
                          mat[1][2] + x * mat[1][0] + y * mat[1][1] +
                          min(0, mat[1][0]) + min(0, mat[1][1])
                      ): tile for ((layer, x, y), tile) in self.tiles.items()}
    self.props = {id: (layer, mat[0][2] + x * mat[0][0] + y * mat[0][1],
                              mat[1][2] + x * mat[1][0] + y * mat[1][1], prop)
                   for (id, (layer, x, y, prop)) in self.props.items()}
    for tile in self.tiles.values():
      tile.transform(mat)
    for (layer, x, y, prop) in self.props.values():
      prop.transform(mat)
    pos = self.start_position()
    self.start_position((mat[0][2] + pos[0] * mat[0][0] + pos[1] * mat[0][1],
                         mat[1][2] + pos[0] * mat[1][0] + pos[1] * mat[1][1]))

    if hasattr(self, "entities"):
      self.entities = {id: (mat[0][2] + x * mat[0][0] + y * mat[0][1],
                            mat[1][2] + x * mat[1][0] + y * mat[1][1], entity)
                     for (id, (x, y, entity)) in self.entities.items()}
      for (x, y, entity) in self.entities.values():
        entity.transform(mat)

    if hasattr(self, "backdrop"):
      self.backdrop.transform(mat)

  def flip_horizontal(self):
    """ Flips the map horizontally. """
    self.transform([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])

  def flip_vertical(self):
    """ Flips the map vertically. """
    self.transform([[1, 0, 0], [0, -1, 0], [0, 0, 1]])

  def rotate(self, times = 1):
    """ Rotates the map 90 degrees `times` times.

    times - The number of 90 degree rotations to perform.  This can be negative.
    """
    cs = [1, 0, -1, 0]
    sn = [0, 1, 0, -1]
    times %= 4
    self.transform([[cs[times], -sn[times], 0], [sn[times], cs[times], 0],
                    [0, 0, 1]])

  def upscale(self, factor):
    """ Increase the size of the map along each axis by `factor`. """
    self.transform([[factor, 0, 0], [0, factor, 0], [0, 0, 1]])
    for ((layer, x, y), tile) in list(self.tiles.items()):
      del self.tiles[(layer, x, y)]
      for (dx, dy, ntile) in tile.upscale(factor):
        self.add_tile(layer, x + dx, y + dy, ntile)

  def calculate_edge_bits(self):
    """ Calculate the proper collision bits on all tiles. """
    dx = [0, 0, -1, 1]
    dy = [-1, 1, 0, 0]
    for ((layer, x, y), tile) in self.tiles.items():
      for side in TileSide:
        if tile_maximal_bits[tile.shape][side] == 15:
          tk = (layer, x + dx[side], y + dy[side])
          if (not tk in self.tiles or
              tile_maximal_bits[self.tiles[tk].shape][side ^ 1] != 15):
            tile.edge_bits(side, tile_maximal_bits[tile.shape][side])
        elif tile_maximal_bits[tile.shape][side]:
          tile.edge_bits(side, tile_maximal_bits[tile.shape][side])
