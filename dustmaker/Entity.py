from .Var import Var, VarType

known_types = []

class Entity:
  @staticmethod
  def _from_raw(type, vars, rotation, unk1, unk2, unk3, unk4):
    for class_type in known_types:
      if type == class_type.TYPE_IDENTIFIER:
        return class_type(vars, rotation, unk1, unk2, unk3, unk4)
    return Entity(type, vars, rotation, unk1, unk2, unk3, unk4)

  def __init__(self, type, vars, rotation = 0,
               unk1 = 0, unk2 = 0, unk3 = 0, unk4 = 0):
    self.type = type
    self.vars = vars
    self.rotation = rotation
    self.unk1 = unk1
    self.unk2 = unk2
    self.unk3 = unk3
    self.unk4 = unk4

  def __repr__(self):
    return "Entity: (%s, %d, %d, %d, %d, %d, %s)" % (
              self.type, self.rotation, self.unk1, self.unk2, self.unk3,
              self.unk4, repr(self.vars))

  def translate(self, x, y):
    pass

  def remap_ids(self, id_map):
    pass

class AIController(Entity):
  TYPE_IDENTIFIER = "AI_controller"

  def __init__(self, vars, rotation = 0,
               unk1 = 0, unk2 = 0, unk3 = 0, unk4 = 0):
    if not 'puppet_id' in vars:
      vars['puppet_id'] = Var(VarType.UINT, 0)
    if not 'nodes' in vars:
      vars['nodes'] = Var(VarType.ARRAY, (VarType.VEC2, []))
    super(AIController, self).__init__(self.TYPE_IDENTIFIER, vars, rotation,
                                       unk1, unk2, unk3, unk4)

  def puppet(self, val = None):
    result = self.vars['puppet_id'].value
    if not val is None:
      self.vars['puppet_id'].value = val
    return result

  def node_count(self):
    return len(self.vars['nodes'].value[1])

  def node_position(self, ind, val = None):
    result = self.vars['nodes'].value[1][ind].value
    if not val is None:
      self.vars['nodes'].value[1][ind] = Var(VarType.VEC2,
                                             (val[0] * 48, val[1] * 48))
    return (result[0] / 48, result[1] / 48)

  def node_append(self, val):
    self.vars['nodes'].value[1].append(Var(VarType.VEC2,
                                           (val[0] * 48, val[1] * 48)))

  def node_pop(self, ind = None):
    return self.vars['nodes'].value[1].pop(ind).value

  def node_clear(self):
    self.vars['nodes'].value[1] = []

  def translate(self, x, y):
    super(AIController, self).translate(x, y)
    for i in range(self.node_count()):
      pos = self.node_position(i)
      self.node_position(i, (pos[0] + x, pos[1] + y))

  def remap_ids(self, id_map):
    self.puppet(id_map[self.puppet()])

known_types.append(AIController)

class CameraNode(Entity):
  TYPE_IDENTIFIER = "camera_node"

  def __init__(self, vars, rotation = 0,
               unk1 = 0, unk2 = 0, unk3 = 0, unk4 = 0):
    if not 'c_node_ids' in vars:
      vars['c_node_ids'] = Var(VarType.ARRAY, (VarType.UINT, []))
    super(CameraNode, self).__init__(self.TYPE_IDENTIFIER, vars, rotation,
                                     unk1, unk2, unk3, unk4)

  def connection_count(self):
    return len(self.vars['c_node_ids'].value[1])

  def connection(self, ind, val = None):
    result = self.vars['c_node_ids'].value[1][ind].value
    if not val is None:
      self.vars['c_node_ids'].value[1][ind] = Var(VarType.UINT, val)
    return result

  def connection_append(self, val):
    self.vars['c_node_ids'].value[1].append(Var(VarType.UINT, val))

  def connection_pop(self, ind = None):
    return self.vars['c_node_ids'].value[1].pop(ind).value

  def connection_clear(self):
    self.vars['c_node_ids'].value[1] = []

  def remap_ids(self, id_map):
    for i in range(self.connection_count()):
      self.connection(i, id_map[self.connection(i)])

known_types.append(CameraNode)

class LevelEnd(Entity):
  TYPE_IDENTIFIER = "level_end"

  def __init__(self, vars, rotation = 0,
               unk1 = 0, unk2 = 0, unk3 = 0, unk4 = 0):
    if not 'ent_list' in vars:
      vars['ent_list'] = Var(VarType.ARRAY, (VarType.UINT, []))
    super(LevelEnd, self).__init__(self.TYPE_IDENTIFIER, vars, rotation,
                                     unk1, unk2, unk3, unk4)

  def entity_count(self):
    return len(self.vars['ent_list'].value[1])

  def entity(self, ind, val = None):
    result = self.vars['ent_list'].value[1][ind].value
    if not val is None:
      self.vars['ent_list'].value[1][ind] = Var(VarType.UINT, val)
    return result

  def entity_append(self, val):
    self.vars['ent_list'].value[1].append(Var(VarType.UINT, val))

  def entity_pop(self, ind = None):
    return self.vars['ent_list'].value[1].pop(ind).value

  def entity_clear(self):
    self.vars['ent_list'].value[1] = []

  def remap_ids(self, id_map):
    for i in range(self.entity_count()):
      self.entity(i, id_map[self.entity(i)])

known_types.append(LevelEnd)
