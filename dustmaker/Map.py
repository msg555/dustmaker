from .MapException import MapException
from .Var import Var, VarType

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

    self.parent = parent
    if not parent:
      self.vars = {}
      self.sshot = b""
      self.entities = {}
      self.backdrop = Map(self)

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

  def add_entity(self, x, y, entity, id = None):
    """ Adds a new entity to the map and returns its id.

        x - The x position in tile units of the entity.
        y - The y position in tile units of the entity.
        entity - The Entity object to add to the map.
        id - The entity identifier.  If set to None the identifier will be
             allocated for you.

        Raises a MapException if the given id is already in use.
    """
    if id is None:
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
    if id is None:
      id = self._next_id()
    else:
      self._note_id(id)
    if id in self.props:
      raise MapException("map already has id")
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
    ix = int(x)
    iy = int(y)
    self.tiles = {(c[0], c[1] + ix, c[2] + iy): tile
                  for (c, tile) in self.tiles.items()}
    self.props = {id: (p[0], p[1] + x, p[2] + y, p[3])
                     for (id, p) in self.props.items()}
    if hasattr(self, "backdrop"):
      pos = self.start_position()
      self.start_position((pos[0] + x, pos[1] + y))
      self.entities = {id: (p[0] + x, p[1] + y, p[2])
                       for (id, p) in self.entities.items()}
      for p in self.entities.values():
        p[2].translate(x, y)
      self.backdrop.translate(x / 16, y / 16)

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
    self.tiles.update(map.tiles)
    self.props.update(map.props)

    if hasattr(self, "backdrop") and hasattr(map, "backdrop"):
      self.entities.update(map.entities)
      self.backdrop.merge_map(map.backdrop, False)
