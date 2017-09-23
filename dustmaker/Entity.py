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

  def access_var(self, vtype, name, val = None, default = None):
    result = default
    if name in self.vars:
      result = self.vars[name].value
    if not val is None:
      if vtype == VarType.INT or vtype == VarType.UINT:
        val = round(val)
      self.vars[name] = Var(vtype, val)
    return result

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

  def access_tile_var(self, vtype, name, val = None, default = None):
    if not val is None:
      val *= 48
    return self.access_var(vtype, name, val, default) / 48.0

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

  def e_rotation(self, val = None):
    return self.access_var(VarType.INT, 'e_rotation', val, 0)

  def draw_depth_sub(self, val = None):
    return self.access_var(VarType.UINT, 'draw_depth_sub', val, 0)

  def r_rotation(self, val = None):
    return self.access_var(VarType.BOOL, 'r_rotation', val, False)

  def r_area(self, val = None):
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

class EndZone(CheckPoint):
  TYPE_IDENTIFIER = "level_end_prox"

  def finished(self, val = None):
    return self.access_var(VarType.BOOL, 'finished', val, false)

known_types.append(EndZone)

class Trigger(Entity):
  TYPE_IDENTIFIER = "base_trigger"

  def width(self, val = None):
    return self.access_tile_var(VarType.INT, 'width', val, 500)

known_types.append(Trigger)

class FogTrigger(Trigger):
  TYPE_IDENTIFIER = "fog_trigger"

  def __init__(self, vars = None, rotation = 0,
               layer = 18, flipX = False, flipY = False, visible = True):
    super(FogTrigger, self).__init__(
        vars, rotation, layer, flipX, flipY, visible)

    grad = self.gradient()
    colours = self.access_array(VarType.UINT, 'fog_colour')
    pers = self.access_array(VarType.FLOAT, 'fog_per')
    while grad.size() < 3:
      grad.append(0)
    while colours.size() < 21:
      colours.append(0x111118)
    while pers.size() < 21:
      pers.append(0.0)

  def _fog_by_index(self, index, val = None):
    if index < 0 or index >= 26 * 21:
      raise IndexError("invalid fog index")

    colours = self.access_array(VarType.UINT, 'fog_colour')
    pers = self.access_array(VarType.FLOAT, 'fog_per')
    while index >= colours.size():
      colours.append(0x111118)
    while index >= pers.size():
      pers.append(0.0)

    result = (colours.get(index), pers.get(index))
    if not val is None:
      colours.set(index, val[0])
      pers.set(index, val[1])
    return result

  def layer_fog(self, layer, val = None):
    return self._fog_by_index(layer, val)

  def sub_layer_fog(self, layer, sublayer, val = None):
    return self._fog_by_index((sublayer + 1) * 21 + layer, val)

  def speed(self, val = None):
    return self.access_var(VarType.FLOAT, 'speed', val, 5)

  def gradient(self):
    return self.access_array(VarType.UINT, 'gradient')

  def gradient_middle(self, val = None):
    return self.access_var(VarType.FLOAT, 'gradient_middle', val, 0)

  def star_bottom(self, val = None):
    return self.access_var(VarType.FLOAT, 'star_bottom', val, 0.0)

  def star_middle(self, val = None):
    return self.access_var(VarType.FLOAT, 'star_middle', val, 0.4)

  def star_top(self, val = None):
    return self.access_var(VarType.FLOAT, 'star_top', val, 1.0)

  def has_sub_layers(self, val = None):
    return self.access_var(VarType.BOOL, 'has_sub_layers', val, False)

known_types.append(FogTrigger)

class AmbienceTrigger(Trigger):
  TYPE_IDENTIFIER = "ambience_trigger"

  def speed(self, val = None):
    return self.access_var(VarType.FLOAT, 'ambience_speed', val, 5)

  def sound_names(self):
    return self.access_array(VarType.STRING, 'sound_ambience_names')

  def sound_vols(self):
    return self.access_array(VarType.FLOAT, 'sound_ambience_vol')

known_types.append(AmbienceTrigger)

class MusicTrigger(Trigger):
  TYPE_IDENTIFIER = "music_trigger"

  def speed(self, val = None):
    return self.access_var(VarType.FLOAT, 'music_speed', val, 5)

  def sound_names(self):
    return self.access_array(VarType.STRING, 'sound_music_names')

  def sound_vols(self):
    return self.access_array(VarType.FLOAT, 'sound_music_vol')

known_types.append(MusicTrigger)

class SpecialTrigger(Trigger):
  TYPE_IDENTIFIER = "special_trigger"

known_types.append(SpecialTrigger)

class TextTrigger(Entity):
  TYPE_IDENTIFIER = "text_trigger"

  def hide(self, val = None):
    return self.access_var(VarType.BOOL, 'hide', val, False)

  def text(self, val = None):
    return self.access_var(VarType.STRING, 'text_string', val, "Blank")

known_types.append(TextTrigger)

class DeathZone(Entity):
  TYPE_IDENTIFIER = "kill_box"

  def width(self, val = None):
    return self.access_tile_var(VarType.INT, 'width', val, 0)

  def height(self, val = None):
    return self.access_tile_var(VarType.INT, 'height', val, 0)

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
    return self.access_var(VarType.INT, 'puppet_id', val, 0)

  def remap_ids(self, id_map):
    if self.puppet() in id_map:
      self.puppet(id_map[self.puppet()])
    else:
      self.puppet(0)

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

  def finished(self, val = None):
    return self.access_var(VarType.BOOL, 'finished', val, false)

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

  def door_set(self, val = None):
    return self.access_var(VarType.UINT, 'door_set', val, 0)

known_types.append(LevelDoor)

class RedKeyDoor(Entity):
  TYPE_IDENTIFIER = "giga_gate"

  def keys_needed(self, val = None):
    return self.access_var(VarType.INT, 'key_needed', val, 1)

known_types.append(RedKeyDoor)

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

  def max_fall_speed(self, val = None):
    return self.access_var(VarType.FLOAT, 'max_fall_speed', val, 800)

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

  def remap_ids(self, id_map):
    if self.door() in id_map:
      self.door(id_map[self.door()])
    else:
      self.door(0)

  def transform(self, mat):
    x = self.lastX()
    y = self.lastY()
    self.lastX(mat[0][2] + x * mat[0][0] + y * mat[0][1])
    self.lastY(mat[1][2] + x * mat[1][0] + y * mat[1][1])

  def door(self, val = None):
    return self.access_var(VarType.UINT, 'door', val, 0)

  def lastX(self, val = None):
    return self.access_var(VarType.FLOAT, 'lastKnowX', val, 0)

  def lastY(self, val = None):
    return self.access_var(VarType.FLOAT, 'lastKnowY', val, 0)

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

""" Missing persist types and vars

custom_score_book
  level_list_id
dustmod_entity_tool
  dm_scale
  target_id
dustmod_trigger
  is_square
filth_switch
  height
  width
z_button
  entity_ids
  start_x
  start_y
z_char_force
  character
z_dash_trigger
  disable
z_kill_trigger
  kill
  only_dustman
  only_enemies
  stun
  stun_direction
  stun_force
  stun_radial
z_level_trigger
  filename
z_particle_trigger
  emitters
  particles
z_physics_trigger
  air_global
  attack_force_heavy
  attack_force_light
  d_dash_max
  d_skill_combo_max
  dash_speed
  di_global
  di_move_max
  di_speed
  di_speed_wall_lock
  fall_accel
  fall_max
  fric_global
  global
  heavy_fall_threshold
  hitrise_speed
  hop_a
  hover_accel
  hover_fall_threshold
  idle_fric
  jump_a
  land_fric
  roof_fric
  roof_run_length
  run_accel
  run_accel_over
  run_global
  run_max
  run_start
  skid_fric
  skid_threshold
  slope_max
  slope_slid_speed
  wall_run_length
  wall_slide_speed
z_respawner
  entity_ids
  max_respawns
  respawn_time
z_scale_trigger
  scale
z_string_list
  list
z_teleport_trigger
  tele_x
  tele_y
z_text_prop_trigger
  colour
  font
  font_size
  layer
  sublayer
  text
  text_rotation
  text_scale
z_wind_generator
  direction
  force
z_wind_trigger
  pressure_accelleration
  pressure_advection
  pressure_diffusion
  velocity_advection
  velocity_diffusion
  velocity_friction_a
  velocity_friction_b
  velocity_friction_c
  vorticity
"""
