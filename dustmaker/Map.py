from .MapException import MapException
from .Var import Var, VarType

class Map:
  def __init__(self, backdrop = False):
    self.tiles = {}
    self.prop_map = {}

    if not backdrop:
      self.vars = {}
      self.sshot = b""
      self.entity_map = {}
      self.backdrop = Map(True)

  def _var_access(self, key, type, val = None, default = None):
    result = default
    if key in self.vars:
      result = self.vars[key].value
    if not val is None:
      self.vars[key] = Var(type, val)
    return result

  def name(self, val = None):
    return self._var_access("level_name", VarType.STRING, val, "")

  def start_position(self, val = None, player = 1):
    result = [0, 0]
    keys = ["p%d_x" % player, "p%d_y" % player]
    for (i, key) in enumerate(keys):
      if key in self.vars:
        result[i] = self.vars[key].value / 48.0
      if not val is None:
        self.vars[key] = Var(VarType.UINT, int(round(val[i] * 48)))
    return (result[0], result[1])

  def virtual_character(self, val = None):
    return self._var_access("vector_character", VarType.BOOL, val, False)

  def add_entity(self, id, x, y, entity):
    if id in self.entity_map:
      raise MapException("map already has id")
    self.entity_map[id] = (x, y, entity)

  def add_prop(self, id, layer, x, y, prop):
    if id in self.prop_map:
      raise MapException("map already has id")
    self.prop_map[id] = (layer, x, y, prop)

  def add_tile(self, layer, x, y, tile):
    if (layer, x, y) in self.tiles:
      raise MapException("tile already exists")
    self.tiles[(layer, x, y)] = tile

  def get_tile(self, layer, x, y):
    return self.tiles[(layer, x, y)]

  def get_prop(self, id):
    return self.prop_map[id][3]

  def get_prop_layer(self, id):
    return self.prop_map[id][0]

  def get_prop_xposition(self, id):
    return self.prop_map[id][1]

  def get_prop_yposition(self, id):
    return self.prop_map[id][2]

  def get_entity(self, id):
    return self.entity_map[id][2]

  def get_entity_xposition(self, id):
    return self.entity_map[id][0]

  def get_entity_yposition(self, id):
    return self.entity_map[id][1]

  def translate(self, x, y):
    ix = int(x)
    iy = int(y)
    self.tiles = {(c[0], c[1] + ix, c[2] + iy): tile
                  for (c, tile) in self.tiles.items()}
    self.prop_map = {id: (p[0], p[1] + x, p[2] + y, p[3])
                     for (id, p) in self.prop_map.items()}
    if hasattr(self, "backdrop"):
      pos = self.start_position()
      self.start_position((pos[0] + x, pos[1] + y))
      self.entity_map = {id: (p[0] + x, p[1] + y, p[2])
                       for (id, p) in self.entity_map.items()}
      for p in self.entity_map.values():
        p[2].translate(x, y)
      self.backdrop.translate(x / 16, y / 16)
