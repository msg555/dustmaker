from MapException import MapException

class Map:
  def __init__(self, backdrop = False):
    self.tiles = {}
    self.prop_map = {}
    self.prop_ids = []

    if not backdrop:
      self.vars = {}
      self.sshot = b""
      self.entity_map = {}
      self.entity_ids = []
      self.backdrop = Map(True)

  def add_entity(self, id, x, y, entity):
    if id in self.entity_map:
      raise MapException("map already has id")

    self.entity_map[id] = (x, y, entity)
    self.entity_ids.append(id)

  def add_prop(self, id, layer, x, y, prop):
    if id in self.prop_map:
      raise MapException("map already has id")

    self.prop_map[id] = (layer, x, y, prop)
    self.prop_ids.append(id)

  def add_tile(self, layer, x, y, tile):
    self.tiles[(layer, x, y)] = tile

  def get_tile(self, layer, x, y):
    return self.tiles[(layer, x, y)]

  def tile_map(self):
    return self.tiles

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
