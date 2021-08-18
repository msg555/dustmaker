"""
Module defining basic entity representations as well as a custom entity
object for each entity in Dustforce.
"""
import copy
import math
from typing import cast, Dict, List, Optional, Tuple, Type, TypeVar

from .enums import CameraNodeType
from .variable import (
    Variable,
    VariableArray,
    VariableBool,
    VariableFloat,
    VariableInt,
    VariableString,
    VariableUInt,
    VariableVec2,
)

TxMatrix = List[List[float]]
T = TypeVar("T")


def bind_prop(
    prop_name: str,
    prop_type: Type[Variable],
    default: T,
    doc: Optional[str] = None,
    objtype=False,
) -> property:
    """Define getters and setters for a named property backed by the map's
    var mapping.
    """

    def _get(self) -> T:
        """get the property with given default"""
        var = self.variables.get(prop_name)
        if var is None:
            result = default() if callable(default) else default
            if objtype:
                self.variables[prop_name] = result
            return result
        if not isinstance(var, prop_type):
            raise ValueError("unexpected property type")
        if objtype:
            return cast(T, var)
        return cast(T, var.value)

    def _set(self, val: T) -> None:
        """set the property"""
        self.variables[prop_name] = val if objtype else prop_type(val)

    def _del(self) -> None:
        """delete the property. Ignored if the property is not set."""
        self.variables.pop(prop_name, None)

    if doc is None:
        doc = f"property '{prop_name}'"

    return property(fget=_get, fset=_set, fdel=_del, doc=doc)


def bind_prop_arr(
    prop_name: str,
    elem_type: Type[Variable],
    doc: Optional[str] = None,
) -> property:
    """Convenience wrapper around bind_prop for array properties"""
    return bind_prop(
        prop_name,
        VariableArray,
        lambda: VariableArray(elem_type),
        doc=doc,
        objtype=True,
    )


class Entity:
    """
    Base class representing an entity object in a map.
    """

    _known_types: Dict[str, Type["Entity"]] = {}

    @classmethod
    def __init_subclass__(cls) -> None:
        """
        Register subclasses as a known type.
        """
        etype = getattr(cls, "TYPE_IDENTIFIER", None)
        if etype is not None:
            cls._known_types[etype] = cls

    @classmethod
    def _from_raw(
        cls,
        etype: str,
        variables: Dict[str, Variable],
        rotation: int,
        layer: int,
        flipX: bool,
        flipY: bool,
        visible: bool,
    ) -> "Entity":
        """Construct an entity from its map format definition."""
        subcls = cls._known_types.get(etype)
        if subcls is not None:
            return subcls(variables, rotation, layer, flipX, flipY, visible)
        entity = Entity(variables, rotation, layer, flipX, flipY, visible)
        entity.etype = etype
        return entity

    def __init__(
        self,
        variables: Optional[Dict[str, Variable]] = None,
        rotation=0,
        layer=18,
        flipX=False,
        flipY=False,
        visible=True,
    ) -> None:
        self.etype: str = getattr(self, "TYPE_IDENTIFIER", "unknown_type")
        self.variables = copy.deepcopy(variables) if variables is not None else {}
        self.rotation = rotation
        self.layer = layer
        self.flipX = flipX
        self.flipY = flipY
        self.visible = visible

    def __repr__(self) -> str:
        return "Entity: (%s, %d, %d, %d, %d, %d, %s)" % (
            self.etype,
            self.rotation,
            self.layer,
            self.flipX,
            self.flipY,
            self.visible,
            repr(self.variables),
        )

    def remap_ids(self, id_map: Dict[int, int]) -> None:
        """Overridable method to allow an entity to remap any internally stored
        IDs."""

    def transform(self, mat: TxMatrix) -> None:
        """Generic transform implementation for entities. Some entity types may
        want to add additional functionality on top of this."""
        angle = math.atan2(mat[1][1], mat[1][0]) - math.pi / 2
        self.rotation = self.rotation - int(0x10000 * angle / math.pi / 2) & 0xFFFF

        if mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0] < 0:
            self.flipY = not self.flipY
            self.rotation = -self.rotation & 0xFFFF


class Emitter(Entity):
    """Emitter entity class"""

    TYPE_IDENTIFIER = "entity_emitter"

    e_rotation = bind_prop("e_rotation", VariableInt, 0)
    draw_depth_sub = bind_prop("draw_depth_sub", VariableUInt, 0)
    r_rotation = bind_prop("r_rotation", VariableBool, False)
    r_area = bind_prop("r_area", VariableBool, False)
    width = bind_prop("width", VariableInt, 480)
    height = bind_prop("height", VariableInt, 480)
    emitter_id = bind_prop("emitter_id", VariableUInt, 0)


class CheckPoint(Entity):
    """Checkpoint entity class"""

    TYPE_IDENTIFIER = "check_point"

    def transform(self, mat):
        """Transform the trigger area"""
        super().transform(mat)

        areas = self.trigger_areas
        for i, pos in enumerate(areas):
            areas[i] = (
                pos[0] * mat[0][0] + pos[1] * mat[0][1],
                pos[0] * mat[1][0] + pos[1] * mat[1][1],
            )

    trigger_areas = bind_prop_arr("trigger_area", VariableVec2)


class EndZone(CheckPoint):
    """Proximity based end zone (purple flag) entity class"""

    TYPE_IDENTIFIER = "level_end_prox"

    finished = bind_prop("finished", VariableBool, False)


class Trigger(Entity):
    """Trigger entity entity class"""

    TYPE_IDENTIFIER = "base_trigger"

    width = bind_prop("width", VariableInt, 500)


class FogTrigger(Trigger):
    """Fog trigger entity class"""

    TYPE_IDENTIFIER = "fog_trigger"

    def _fog_by_index(
        self, index: int, val: Optional[Tuple[int, float]]
    ) -> Tuple[int, float]:
        """Internal method to get the fog values at a given index corresponding
        to either a layer or sublayer"""
        if index < 0 or index >= 26 * 21:
            raise IndexError("invalid fog index")

        colours = self.variables.setdefault("fog_trigger", VariableArray(VariableUInt))
        if not isinstance(colours, VariableArray):
            raise ValueError("fog_trigger variable not an array")
        pers = self.variables.setdefault("fog_per", VariableArray(VariableFloat))
        if not isinstance(pers, VariableArray):
            raise ValueError("fog_per variable not an array")

        while index >= len(colours):
            colours.append(0x111118)
        while index >= len(pers):
            pers.append(0.0)

        result = (colours[index], pers[index])
        if val is not None:
            colours[index], pers[index] = val
        return result

    def layer_fog(
        self, layer: int, val: Optional[Tuple[int, float]] = None
    ) -> Tuple[int, float]:
        """Get/set the fog colour and percentage for a given layer."""
        return self._fog_by_index(layer, val)

    def sub_layer_fog(
        self, layer: int, sublayer: int, val: Optional[Tuple[int, float]] = None
    ) -> Tuple[int, float]:
        """Get/set the fog colour and percentage for a given sub-layer."""
        return self._fog_by_index((sublayer + 1) * 21 + layer, val)

    speed = bind_prop("speed", VariableFloat, 5.0)
    gradient = bind_prop_arr("gradient", VariableUInt)
    gradient_middle = bind_prop("gradient_middle", VariableFloat, 0.0)
    star_bottom = bind_prop("star_bottom", VariableFloat, 0.0)
    star_middle = bind_prop("star_middle", VariableFloat, 0.4)
    star_top = bind_prop("star_top", VariableFloat, 1.0)
    has_sub_layers = bind_prop("has_sub_layers", VariableBool, False)


class AmbienceTrigger(Trigger):
    """Ambience trigger entity class"""

    TYPE_IDENTIFIER = "ambience_trigger"

    speed = bind_prop("ambience_speed", VariableFloat, 5)
    sound_names = bind_prop_arr("sound_ambience_names", VariableString)
    sound_vols = bind_prop_arr("sound_ambience_vol", VariableFloat)


class MusicTrigger(Trigger):
    """Music trigger entity class"""

    TYPE_IDENTIFIER = "music_trigger"

    speed = bind_prop("music_speed", VariableFloat, 5)
    sound_names = bind_prop_arr("sound_music_names", VariableString)
    sound_vols = bind_prop_arr("sound_music_vol", VariableFloat)


class SpecialTrigger(Trigger):
    """Max special trigger entity class"""

    TYPE_IDENTIFIER = "special_trigger"


class TextTrigger(Entity):
    """Text trigger entity class"""

    TYPE_IDENTIFIER = "text_trigger"

    hide = bind_prop("hide", VariableBool, False)
    text = bind_prop("text_string", VariableString, b"")


class DeathZone(Entity):
    """Death zone entity class"""

    TYPE_IDENTIFIER = "kill_box"

    def transform(self, mat: TxMatrix) -> None:
        """Transform the death zone width and height"""
        super().transform(mat)
        w = self.width
        h = self.height
        self.width = abs(w * mat[0][0] + h * mat[0][1])
        self.height = abs(w * mat[1][0] + h * mat[1][1])

    width = bind_prop("width", VariableInt, 0)
    height = bind_prop("height", VariableInt, 0)


class AIController(Entity):
    """AI controller node entity class"""

    TYPE_IDENTIFIER = "AI_controller"

    def remap_ids(self, id_map: Dict[int, int]) -> None:
        """Remap the puppet id."""
        super().remap_ids(id_map)
        self.puppet = id_map.get(self.puppet, 0)

    def transform(self, mat: TxMatrix) -> None:
        """Transform the controller waypoints."""
        super().transform(mat)

        nodes = self.nodes
        for i, pos in enumerate(nodes):
            nodes[i] = (
                mat[0][2] + pos[0] * mat[0][0] + pos[1] * mat[0][1],
                mat[1][2] + pos[0] * mat[1][0] + pos[1] * mat[1][1],
            )

    nodes = bind_prop_arr("nodes", VariableVec2)
    node_wait_times = bind_prop_arr("nodes_wait_time", VariableInt)
    puppet = bind_prop("puppet_id", VariableUInt, 0)


class CameraNode(Entity):
    """Camera node entity class"""

    TYPE_IDENTIFIER = "camera_node"

    def remap_ids(self, id_map: Dict[int, int]) -> None:
        """Remap the connected camera node IDs."""
        super().remap_ids(id_map)
        nds = self.nodes
        for i, nd_id in enumerate(nds):
            nds[i] = id_map.get(nd_id, 0)

    def transform(self, mat: TxMatrix) -> None:
        """Transform the camera zoom and width"""
        scale = math.sqrt(abs(mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0]))
        self.zoom(self.zoom() * scale)
        self.width(self.width() * scale)

    node_type = bind_prop(
        "node_type",
        VariableInt,
        CameraNodeType.NORMAL,
        "camera node type, see CameraNodeType enum",
    )
    test_widths = bind_prop_arr("test_widths", VariableInt)
    nodes = bind_prop_arr("c_node_ids", VariableUInt)
    control_widths = bind_prop_arr("control_widths", VariableVec2)
    zoom = bind_prop("zoom_h", VariableInt, 1080)
    width = bind_prop("width", VariableInt, 520)


class LevelEnd(Entity):
    """Level end flag class"""

    TYPE_IDENTIFIER = "level_end"

    def remap_ids(self, id_map: Dict[int, int]) -> None:
        """Remap entity IDs attached to this flag."""
        super().remap_ids(id_map)
        ents = self.entities
        for i, ent_id in enumerate(ents):
            ents[i] = id_map.get(ent_id, 0)

    entities = bind_prop_arr("ent_list", VariableUInt)
    finished = bind_prop("finished", VariableBool, False)


class ScoreBook(Entity):
    """Score book class"""

    TYPE_IDENTIFIER = "score_book"

    book_type = bind_prop("book_type", VariableString, b"")


class LevelDoor(Trigger):
    """Level door class"""

    TYPE_IDENTIFIER = "level_door"

    file_name = bind_prop("file_name", VariableString, b"")
    door_set = bind_prop("door_set", VariableUInt, 0)


class RedKeyDoor(Entity):
    """Red key door class"""

    TYPE_IDENTIFIER = "giga_gate"

    keys_needed = bind_prop("key_needed", VariableInt, 1)


class Enemy(Entity):
    """Base class for all enemy types"""

    FILTH = 1


class EnemyLightPrism(Enemy):
    """Light prism entity class"""

    TYPE_IDENTIFIER = "enemy_tutorial_square"


class EnemyHeavyPrism(Enemy):
    """Heavy prism entity class"""

    TYPE_IDENTIFIER = "enemy_tutorial_hexagon"


class EnemySlimeBeast(Enemy):
    """Slime beast entity class"""

    TYPE_IDENTIFIER = "enemy_slime_beast"

    FILTH = 9


class EnemySlimeBarrel(Enemy):
    """Slime barrel (paint can) entity class"""

    TYPE_IDENTIFIER = "enemy_slime_barrel"

    FILTH = 3


class EnemySpringBall(Enemy):
    """Spring ball/blob entity class"""

    TYPE_IDENTIFIER = "enemy_spring_ball"

    FILTH = 5


class EnemySlimeBall(Enemy):
    """Slime ball (lab turkey) entity class"""

    TYPE_IDENTIFIER = "enemy_slime_ball"

    FILTH = 3


class EnemyTrashTire(Enemy):
    """Trash tire entity class"""

    TYPE_IDENTIFIER = "enemy_trash_tire"

    FILTH = 3

    max_fall_speed = bind_prop("max_fall_speed", VariableFloat, 800.0)


class EnemyTrashBeast(Enemy):
    """Trash beast (golem) entity class"""

    TYPE_IDENTIFIER = "enemy_trash_beast"

    FILTH = 9


class EnemyTrashCan(Enemy):
    """Trash can entity class"""

    TYPE_IDENTIFIER = "enemy_trash_can"

    FILTH = 9


class EnemyTrashBall(Enemy):
    """Trash ball entity class"""

    TYPE_IDENTIFIER = "enemy_trash_ball"

    FILTH = 3


class EnemyBear(Enemy):
    """Bear entity class"""

    TYPE_IDENTIFIER = "enemy_bear"

    FILTH = 9


class EnemyTotemLarge(Enemy):
    """Large totem (stoneboss) entity class"""

    TYPE_IDENTIFIER = "enemy_stoneboss"

    FILTH = 12


class EnemyTotemSmall(Enemy):
    """Totem entity class"""

    TYPE_IDENTIFIER = "enemy_stonebro"

    FILTH = 3


class EnemyPorcupine(Enemy):
    """Porcupine entity class"""

    TYPE_IDENTIFIER = "enemy_porcupine"


class EnemyWolf(Enemy):
    """Wolf entity class"""

    TYPE_IDENTIFIER = "enemy_wolf"

    FILTH = 5


class EnemyTurkey(Enemy):
    """Turkey (critter) entity class"""

    TYPE_IDENTIFIER = "enemy_critter"

    FILTH = 3


class EnemyFlag(Enemy):
    """Flag entity class"""

    TYPE_IDENTIFIER = "enemy_flag"

    FILTH = 5


class EnemyScroll(Enemy):
    """Scroll entity class"""

    TYPE_IDENTIFIER = "enemy_scrolls"


class EnemyTreasure(Enemy):
    """Treasure entity class"""

    TYPE_IDENTIFIER = "enemy_treasure"


class EnemyChestTreasure(Enemy):
    """Chest that spawns treasures entity class"""

    TYPE_IDENTIFIER = "enemy_chest_treasure"

    FILTH = 9


class EnemyChestScrolls(Enemy):
    """Chest that spawns scross entity class"""

    TYPE_IDENTIFIER = "enemy_chest_scrolls"

    FILTH = 9


class EnemyButler(Enemy):
    """Butler entity class"""

    TYPE_IDENTIFIER = "enemy_butler"


class EnemyMaid(Enemy):
    """Maid entity class"""

    TYPE_IDENTIFIER = "enemy_maid"


class EnemyKnight(Enemy):
    """Knign entity class"""

    TYPE_IDENTIFIER = "enemy_knight"

    FILTH = 9


class EnemyGargoyleBig(Enemy):
    """Big (punching) gargoyle entity class"""

    TYPE_IDENTIFIER = "enemy_gargoyle_big"

    FILTH = 5


class EnemyGargoyleSmall(Enemy):
    """Gargoyle (mansion turkey) entity class"""

    TYPE_IDENTIFIER = "enemy_gargoyle_small"

    FILTH = 3


class EnemyBook(Enemy):
    """Book entity class"""

    TYPE_IDENTIFIER = "enemy_book"

    FILTH = 3


class EnemyHawk(Enemy):
    """Hawk entity class"""

    TYPE_IDENTIFIER = "enemy_hawk"

    FILTH = 3


class EnemyKey(Enemy):
    """Key entity class"""

    TYPE_IDENTIFIER = "enemy_key"

    FILTH = 1

    def remap_ids(self, id_map: Dict[int, int]) -> None:
        """Remap the door ID."""
        super().remap_ids(id_map)
        self.door = id_map.get(self.door, 0)

    def transform(self, mat: TxMatrix) -> None:
        """Transform the last know coordinates."""
        super().transform(mat)

        x = self.lastX
        y = self.lastY
        self.lastX = mat[0][2] + x * mat[0][0] + y * mat[0][1]
        self.lastY = mat[1][2] + x * mat[1][0] + y * mat[1][1]

    door = bind_prop("door", VariableUInt, 0, "ID of door entity")
    lastX = bind_prop("lastKnowX", VariableFloat, 0.0)
    lastY = bind_prop("lastKnowY", VariableFloat, 0.0)


class EnemyDoor(Enemy):
    """Door entity class"""

    TYPE_IDENTIFIER = "enemy_door"

    FILTH = 0


class Apple(Entity):
    """Apple entity class"""

    TYPE_IDENTIFIER = "hittable_apple"


class Dustman(Entity):
    """Dustman entity class"""

    TYPE_IDENTIFIER = "dust_man"


class Dustgirl(Entity):
    """Dustgirl entity classs"""

    TYPE_IDENTIFIER = "dust_girl"


class Dustkid(Entity):
    """Dustkid entity class"""

    TYPE_IDENTIFIER = "dust_kid"


class Dustworth(Entity):
    """Dustworth entity class"""

    TYPE_IDENTIFIER = "dust_worth"


class Dustwraith(Entity):
    """Dustwraith entity class"""

    TYPE_IDENTIFIER = "dust_wraith"


class Leafsprite(Entity):
    """Leaf sprite entity class"""

    TYPE_IDENTIFIER = "leaf_sprite"


class Trashking(Entity):
    """Trash king entity class"""

    TYPE_IDENTIFIER = "trash_king"


class Slimeboss(Entity):
    """Slime boss entity class"""

    TYPE_IDENTIFIER = "slime_boss"


_NOTES = """ Missing persist types and vars

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
