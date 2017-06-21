from .Var import Var, VarType

import math
import copy

known_types = []

class EntityVarArray:
  def __init__(self, arr, atype):
    self.arr = arr
    self.atype = atype

  def get(self, ind, val = None):
    result = self.arr.value[1][ind].value
    if not val is None:
      self.arr.value[1][ind].value = val
    return result

  def set(self, ind, val):
    return self.get(ind, val)

  def size(self): return len(self.arr.value[1])
  def count(self): return self.size()
  def length(self): return self.size()

  def append(self, val):
    self.arr.value[1].append(Var(self.atype, val))

  def pop(self, ind = None):
    return arr.value[1].pop(ind)

class Entity:
  @staticmethod
  def _from_raw(type, vars, rotation, layer, flipX, flipY, visible):
    for class_type in known_types:
      if type == class_type.TYPE_IDENTIFIER:
        return class_type(vars, rotation, layer, flipX, flipY, visible)
    entity = Entity(vars, rotation, layer, flipX, flipY, visible)
    entity.type = type
    return entity

  def __init__(self, vars = None, rotation = 0,
               layer = 18, flipX = False, flipY = False, visible = True):
    if hasattr(self, "TYPE_IDENTIFIER"):
      self.type = self.TYPE_IDENTIFIER
    vars = copy.deepcopy(vars) if vars is not None else {}
    self.vars = vars
    self.rotation = rotation
    self.layer = layer
    self.flipX = flipX
    self.flipY = flipY
    self.visible = visible

  def __repr__(self):
    return "Entity: (%s, %d, %d, %d, %d, %d, %s)" % (
              self.type, self.rotation, self.layer, self.flipX, self.flipY,
              self.visible, repr(self.vars))

  def remap_ids(self, id_map):
    pass

  def transform(self, mat):
    angle = math.atan2(mat[1][1], mat[1][0]) - math.pi / 2
    self.rotation = self.rotation - int(0x10000 * angle / math.pi / 2) & 0xFFFF

    if mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0] < 0:
      self.flipY = not self.flipY
      self.rotation = -self.rotation & 0xFFFF

  def access_var(self, vtype, name, val = None, default = None):
    result = default
    if name in self.vars:
      result = self.vars[name].value
    if not val is None:
      self.vars[name] = Var(vtype, val)
    return result

  def access_tile_var(self, vtype, name, val = None, default = None):
    if not val is None:
      val *= 48
      if vtype == VarType.INT or vtype == VarType.UINT:
        val = round(val)
    return self.access_var(vtype, name, val, default) * 48

  def access_array(self, atype, name):
    if not name in self.vars:
      self.vars[name] = Var(VarType.ARRAY, (atype, []))
    return EntityVarArray(self.vars[name], atype)

class Emitter(Entity):
  TYPE_IDENTIFIER = "entity_emitter"

  def __init__(self, vars = None, rotation = 0,
               layer = 18, flipX = False, flipY = False, visible = True):
    vars = copy.deepcopy(vars) if vars is not None else {}
    super(Emitter, self).__init__(vars, rotation, layer, flipX, flipY, visible)

  def e_rotation(self, val):
    return self.access_var(VarType.INT, 'e_rotation', val, 0)

  def draw_depth_sub(self, val):
    return self.access_var(VarType.UINT, 'draw_depth_sub', val, 0)

  def r_rotation(self, val):
    return self.access_var(VarType.BOOL, 'r_rotation', val, False)

  def r_area(self, val):
    return self.access_var(VarType.BOOL, 'r_area', val, False)

  def width(self, val = None):
    return self.access_tile_var(VarType.INT, 'width', val, 480)

  def height(self, val = None):
    return self.access_tile_var(VarType.INT, 'height', val, 480)

  def emitter_id(self, val = None):
    return self.access_var(VarType.UINT, 'emitter_id', val, 0)

known_types.append(Emitter)

class TriggerArea(Entity):
  def trigger_areas(self):
    return self.access_array(VarType.VEC2, 'trigger_area')

  def transform(self, mat):
    areas = self.trigger_areas()
    for i in range(areas.count()):
      pos = areas.get(i)
      areas.set(i,
          (pos[0] * mat[0][0] + pos[1] * mat[0][1],
           pos[0] * mat[1][0] + pos[1] * mat[1][1]))
    super(TriggerArea, self).transform(mat)

class CheckPoint(TriggerArea):
  TYPE_IDENTIFIER = "check_point"

known_types.append(CheckPoint)

class EndZone(TriggerArea):
  TYPE_IDENTIFIER = "level_end_prox"

known_types.append(EndZone)

class Trigger(Entity):
  def width(self, val = None):
    return self.access_tile_var(VarType.INT, 'width', val, 500)

class FogTrigger(Trigger):
  TYPE_IDENTIFIER = "fog_trigger"

known_types.append(FogTrigger)

class SpecialTrigger(Trigger):
  TYPE_IDENTIFIER = "special_trigger"

known_types.append(SpecialTrigger)

class DeathZone(Entity):
  TYPE_IDENTIFIER = "kill_box"

  def width(self, val = None):
    return self.access_tile_var('width', val)

  def height(self, val = None):
    return self.access_tile_var('height', val)

  def transform(self, mat):
    w = self.width()
    h = self.height()
    self.width(abs(w * mat[0][0] + h * mat[0][1]))
    self.height(abs(w * mat[1][0] + h * mat[1][1]))
    super(DeathZone, self).transform(mat)

known_types.append(DeathZone)

class AIController(Entity):
  TYPE_IDENTIFIER = "AI_controller"

  def nodes(self):
    return self.access_array(VarType.VEC2, 'nodes')

  def node_wait_times(self):
    return self.access_array(VarType.INT, 'nodes_wait_time')

  def puppet(self, val = None):
    return self.access_var(VarType.INT, 'puppet', val, 0)

  def remap_ids(self, id_map):
    if self.puppet() in id_map:
      self.puppet(id_map[self.puppet()])
    else:
      self.puppet(-1)

  def transform(self, mat):
    nods = self.nodes()
    for i in range(nods.count()):
      pos = nods.get(i)
      nods.set(i,
          (mat[0][2] + pos[0] * mat[0][0] + pos[1] * mat[0][1],
           mat[1][2] + pos[0] * mat[1][0] + pos[1] * mat[1][1]))
    super(AIController, self).transform(mat)

known_types.append(AIController)

class CameraNode(Entity):
  TYPE_IDENTIFIER = "camera_node"

  NODE_TYPE_NORMAL = 1
  NODE_TYPE_DETACH = 2
  NODE_TYPE_CONNECT = 3
  NODE_TYPE_INTEREST = 4
  NODE_TYPE_FORCE_CONNECT = 5

  def test_widths(self):
    return self.access_array(VarType.INT, 'test_width')

  def nodes(self):
    return self.access_array(VarType.UINT, 'c_node_ids')

  def control_widths(self):
    return self.access_array(VarType.VEC2, 'control_width')

  def node_type(self, val = None):
    return self.access_var(VarType.INT, 'node_type', val,
          CameraNode.NODE_TYPE_NORMAL)

  def zoom(self, val = None):
    return self.access_var(VarType.INT, 'zoom_h', val, 1080)

  def width(self, val = None):
    return self.access_tile_var(VarType.INT, 'width', val, 520)

  def remap_ids(self, id_map):
    nds = self.nodes()
    for i in range(nds.count()):
      nds.set(i, id_map[nds.get(i)])

  def transform(self, mat):
    scale = math.sqrt(abs(mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0]))
    self.zoom(self.zoom() * scale)
    self.width(self.width() * scale)

known_types.append(CameraNode)

class LevelEnd(Entity):
  TYPE_IDENTIFIER = "level_end"

  def entities(self):
    return self.access_array(VarType.UINT, 'ent_list')

  def remap_ids(self, id_map):
    ents = self.entities()
    for i in range(ents.count()):
      ents.set(i, id_map[ents.get(i)])

known_types.append(LevelEnd)

class ScoreBook(Entity):
  TYPE_IDENTIFIER = "score_book"

  def book_type(self, val):
    return self.access_var(VarType.STRING, 'book_type', val, "")

known_types.append(ScoreBook)

class LevelDoor(Trigger):
  TYPE_IDENTIFIER = "level_door"

  def file_name(self, val = None):
    return self.access_var(VarType.STRING, 'file_name', val, "")

  def width(self, val = None):
    return self.access_tile_var(VarType.INT, 'width', val, 100)

  def door_set(self, val = None):
    return self.access_var(VarType.UINT, 'door_set', val, 0)

known_types.append(LevelDoor)

class Enemy(Entity):
  def filth(self):
    return 1

  def combo(self):
    return self.filth()

class EnemyLightPrism(Enemy):
  TYPE_IDENTIFIER = "enemy_tutorial_square"

class EnemyHeavyPrism(Enemy):
  TYPE_IDENTIFIER = "enemy_tutorial_hexagon"
  def combo(self): return 3

class EnemySlimeBeast(Enemy):
  TYPE_IDENTIFIER = "enemy_slime_beast"
  def filth(self): return 9

class EnemySlimeBarrel(Enemy):
  TYPE_IDENTIFIER = "enemy_slime_barrel"
  def filth(self): return 3

class EnemySpringBall(Enemy):
  TYPE_IDENTIFIER = "enemy_spring_ball"
  def filth(self): return 5

class EnemySlimeBall(Enemy):
  TYPE_IDENTIFIER = "enemy_slime_ball"
  def filth(self): return 3

class EnemyTrashTire(Enemy):
  TYPE_IDENTIFIER = "enemy_trash_tire"
  def filth(self): return 3

class EnemyTrashBeast(Enemy):
  TYPE_IDENTIFIER = "enemy_trash_beast"
  def filth(self): return 9

class EnemyTrashCan(Enemy):
  TYPE_IDENTIFIER = "enemy_trash_can"
  def filth(self): return 9

class EnemyTrashBall(Enemy):
  TYPE_IDENTIFIER = "enemy_trash_ball"
  def filth(self): return 3

class EnemyBear(Enemy):
  TYPE_IDENTIFIER = "enemy_bear"
  def filth(self): return 9

class EnemyTotemLarge(Enemy):
  TYPE_IDENTIFIER = "enemy_stoneboss"
  def filth(self): return 12

class EnemyTotemSmall(Enemy):
  TYPE_IDENTIFIER = "enemy_stonebro"
  def filth(self): return 3

class EnemyPorcupine(Enemy):
  TYPE_IDENTIFIER = "enemy_porcupine"

class EnemyWolf(Enemy):
  TYPE_IDENTIFIER = "enemy_wolf"
  def filth(self): return 5

class EnemyTurkey(Enemy):
  TYPE_IDENTIFIER = "enemy_critter"
  def filth(self): return 3

class EnemyFlag(Enemy):
  TYPE_IDENTIFIER = "enemy_flag"
  def filth(self): return 5

class EnemyScroll(Enemy):
  TYPE_IDENTIFIER = "enemy_scrolls"

class EnemyTreasure(Enemy):
  TYPE_IDENTIFIER = "enemy_treasure"

class EnemyChestTreasure(Enemy):
  TYPE_IDENTIFIER = "enemy_chest_treasure"
  def filth(self): return 9

class EnemyChestScrolls(Enemy):
  TYPE_IDENTIFIER = "enemy_chest_scrolls"
  def filth(self): return 9

class EnemyButler(Enemy):
  TYPE_IDENTIFIER = "enemy_butler"

class EnemyMaid(Enemy):
  TYPE_IDENTIFIER = "enemy_maid"

class EnemyKnight(Enemy):
  TYPE_IDENTIFIER = "enemy_knight"
  def filth(self): return 9

class EnemyGargoyleBig(Enemy):
  TYPE_IDENTIFIER = "enemy_gargoyle_big"
  def filth(self): return 5

class EnemyGargoyleSmall(Enemy):
  TYPE_IDENTIFIER = "enemy_gargoyle_small"
  def filth(self): return 3

class EnemyBook(Enemy):
  TYPE_IDENTIFIER = "enemy_book"
  def filth(self): return 3

class EnemyHawk(Enemy):
  TYPE_IDENTIFIER = "enemy_hawk"
  def filth(self): return 3

class EnemyKey(Enemy):
  TYPE_IDENTIFIER = "enemy_key"
  def filth(self): return 1

class EnemyDoor(Enemy):
  TYPE_IDENTIFIER = "enemy_door"
  def filth(self): return 0

known_types.append(EnemyLightPrism)
known_types.append(EnemyHeavyPrism)
known_types.append(EnemySlimeBeast)
known_types.append(EnemySlimeBarrel)
known_types.append(EnemySpringBall)
known_types.append(EnemySlimeBall)
known_types.append(EnemyTrashTire)
known_types.append(EnemyTrashBeast)
known_types.append(EnemyTrashCan)
known_types.append(EnemyTrashBall)
known_types.append(EnemyBear)
known_types.append(EnemyTotemLarge)
known_types.append(EnemyTotemSmall)
known_types.append(EnemyPorcupine)
known_types.append(EnemyWolf)
known_types.append(EnemyTurkey)
known_types.append(EnemyFlag)
known_types.append(EnemyScroll)
known_types.append(EnemyTreasure)
known_types.append(EnemyChestTreasure)
known_types.append(EnemyChestScrolls)
known_types.append(EnemyButler)
known_types.append(EnemyMaid)
known_types.append(EnemyKnight)
known_types.append(EnemyGargoyleBig)
known_types.append(EnemyGargoyleSmall)
known_types.append(EnemyBook)
known_types.append(EnemyHawk)
known_types.append(EnemyKey)
known_types.append(EnemyDoor)

class Apple(Entity):
  TYPE_IDENTIFIER = "hittable_apple"

class Dustman(Entity):
  TYPE_IDENTIFIER = "dust_man"

class Dustgirl(Entity):
  TYPE_IDENTIFIER = "dust_girl"

class Dustkid(Entity):
  TYPE_IDENTIFIER = "dust_kid"

class Dustworth(Entity):
  TYPE_IDENTIFIER = "dust_worth"

class Dustwraith(Entity):
  TYPE_IDENTIFIER = "dust_wraith"

class Leafsprite(Entity):
  TYPE_IDENTIFIER = "leaf_sprite"

class Trashking(Entity):
  TYPE_IDENTIFIER = "trash_king"

class Slimeboss(Entity):
  TYPE_IDENTIFIER = "slime_boss"

known_types.append(Apple)
known_types.append(Dustman)
known_types.append(Dustgirl)
known_types.append(Dustkid)
known_types.append(Dustworth)
known_types.append(Dustwraith)
known_types.append(Leafsprite)
known_types.append(Trashking)
known_types.append(Slimeboss)
