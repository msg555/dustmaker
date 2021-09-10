"""
Module defining basic entity representations as well as a custom entity
object for each entity in Dustforce.
"""
import copy
from enum import IntEnum
import math
from typing import cast, Dict, Optional, Tuple, Type, TypeVar

from .transform import TxMatrix
from .variable import (
    Variable,
    VariableArray,
    VariableBool,
    VariableFloat,
    VariableInt,
    VariableString,
    VariableStruct,
    VariableUInt,
    VariableVec2,
)

T = TypeVar("T")


def _get_python_prop_type(prop_type: Type[Variable]) -> str:
    """Returns the python type name for variable types for use
    with documentation."""
    if prop_type is VariableBool:
        return "bool"
    if prop_type in (VariableInt, VariableUInt):
        return "int"
    if prop_type is VariableFloat:
        return "float"
    if prop_type is VariableString:
        return "bytes"
    if prop_type is VariableVec2:
        return "(float, float)"
    if prop_type is VariableStruct:
        return "dict[str, Variable]"
    if prop_type is VariableArray:
        return "MutableSequence"
    raise TypeError("unexpected variable type")


def bind_prop(
    prop_name: str,
    prop_type: Type[Variable],
    default: T,
    doc: Optional[str] = None,
    doc_add_type=True,
    objtype=False,
) -> property:
    """Define getters and setters for a named property backed by the map's
    var mapping.

    :meta private:
    """

    # Removed "-> T" type annotation on this because it was making docs ugly.
    def _get(self):
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
        doc = f"Wrapper around `variables['{prop_name}']` of type :class:`{prop_type.__name__}`."
    if doc_add_type:
        doc = f"{_get_python_prop_type(prop_type)}: {doc}"
    if not objtype:
        doc = f"{doc} Defaults to `{default}`."

    return property(fget=_get, fset=_set, fdel=_del, doc=doc)


def bind_prop_arr(
    prop_name: str,
    elem_type: Type[Variable],
    doc: Optional[str] = None,
    doc_add_type=True,
) -> property:
    """Convenience wrapper around bind_prop for array properties

    :meta private:
    """
    if doc is None:
        doc = f"Wrapper around `variables['{prop_name}']` of type `VariableArray[{elem_type.__name__}]`."
    if doc_add_type:
        doc = f"MutableSequence[{_get_python_prop_type(elem_type)}]: {doc}"

    return bind_prop(
        prop_name,
        VariableArray,
        lambda: VariableArray(elem_type),
        doc=doc,
        doc_add_type=False,
        objtype=True,
    )


class Entity:
    """Base class representing an entity object in a map. Commonly used
    entities have subclasses of :class:`Entity` to represent them. Those that
    do not will simply be of type :class:`Entity` and have their :attr:`etype`
    field set to control how the Dustforce engine will interpret the entity.

    To add new Entity types simply extend this class and include a `TYPE_IDENTIFIER`
    class attribute that matches the type identifier used internally by Dustforce.
    The level reader and writer will then automatically use these types (as long as
    the classes have been initialized). Additionally you can override the
    :meth:`remap_ids` and :meth:`transform` methods to handle any special processing
    this entity type requires. If you make these changes consider contributing your
    entity specialization as a pull request.

    Attributes:
        etype (str): The entity type name. This typically matches the `TYPE_IDENTIFIER`
            attribute of the concrete type of this object.
        variables (dict[str, Variable]): Persist data variable mapping for this entity
        rotation (16-bit uint): Clockwise rotation of the entity ranging from 0 to 0xFFFF.
            0x4000 corresponds to a 90 degree rotation, 0x8000 to 180 degrees, 0xC000
            to 270 degrees. This rotation is logically applied after any flips have
            been applied.
        layer (8-bit uint): Layer to render the entity in
        flip_x (bool): Flip the entity horizontally
        flip_y (bool): Flip the entity vertically
        visible (bool): Is the entity visible
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
        flip_x: bool,
        flip_y: bool,
        visible: bool,
    ) -> "Entity":
        """Construct an entity from its map format definition."""
        subcls = cls._known_types.get(etype)
        if subcls is not None:
            return subcls(variables, rotation, layer, flip_x, flip_y, visible)
        entity = Entity(variables, rotation, layer, flip_x, flip_y, visible)
        entity.etype = etype
        return entity

    def __init__(
        self,
        variables: Optional[Dict[str, Variable]] = None,
        rotation=0,
        layer=18,
        flip_x=False,
        flip_y=False,
        visible=True,
    ) -> None:
        self.etype = getattr(self, "TYPE_IDENTIFIER", "unknown_type")
        self.variables = copy.deepcopy(variables) if variables is not None else {}
        self.rotation = rotation
        self.layer = layer
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.visible = visible

    def __repr__(self) -> str:
        return "Entity: (%s, %d, %d, %d, %d, %d, %s)" % (
            self.etype,
            self.rotation,
            self.layer,
            self.flip_x,
            self.flip_y,
            self.visible,
            repr(self.variables),
        )

    def remap_ids(self, id_map: Dict[int, int]) -> None:
        """Overridable method to allow an entity to remap any internally stored
        IDs."""

    def transform(self, mat: TxMatrix) -> None:
        """Generic transform implementation for entities. Transforms the Entity
        :attr:`rotation` and :attr:`flip_y` attributes (:attr:`flip_x` is redundant).

        Many subtypes will perform additional transformations on their :attr:`variables`.
        """
        self.rotation = self.rotation - int(0x10000 * mat.angle / math.pi / 2) & 0xFFFF
        if mat.flipped:
            self.flip_y = not self.flip_y
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

    def transform(self, mat: TxMatrix) -> None:
        """Transform the trigger area"""
        super().transform(mat)

        areas = self.trigger_areas
        for i, pos in enumerate(areas):
            # trigger_area locations are relative the entity itself so should
            # not be sampled with offset.
            areas[i] = mat.sample(*pos, with_offset=False)

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

    def normalize(self) -> None:
        """Resizes :attr:`colours` and :attr:`pers` arrays to be the
        correct length for the given :attr:`has_sub_layers` setting.
        """
        want_length = 21 * 26 if self.has_sub_layers else 21
        while len(self.colours) > want_length:
            self.colours.pop()
        while len(self.pers) > want_length:
            self.pers.pop()
        while len(self.colours) < want_length:
            self.colours.append(0x111118)
        while len(self.pers) < want_length:
            self.pers.append(0.0)

    @staticmethod
    def get_layer_index(layer: int, sublayer: Optional[int] = None) -> int:
        """Helper function to find fog data for a given layer/sublayer.

        Arguments:
            layer (int): Must be between 0 and 20 inclusive.
            sublayer (int): Must be between 0 and 24 inclusive.

        Returns:
            Index into :attr:`colours` and :attr:`pers` where fog data is
            stored for the given `layer` and (if present) `sublayer`.
        """
        assert 0 <= layer <= 20
        if sublayer is None:
            return layer
        assert 0 <= sublayer <= 20
        return (sublayer + 1) * 21 + layer

    speed = bind_prop("speed", VariableFloat, 5.0)
    gradient = bind_prop_arr("gradient", VariableUInt)
    gradient_middle = bind_prop("gradient_middle", VariableFloat, 0.0)
    star_bottom = bind_prop("star_bottom", VariableFloat, 0.0)
    star_middle = bind_prop("star_middle", VariableFloat, 0.4)
    star_top = bind_prop("star_top", VariableFloat, 1.0)
    has_sub_layers = bind_prop(
        "has_sub_layers",
        VariableBool,
        False,
        "Controls if sublayer fog data is enabled for this trigger",
    )
    colours = bind_prop_arr(
        "fog_trigger",
        VariableUInt,
        "Fog colour in 0xRRGGBB format for each (sub)layer.",
    )
    pers = bind_prop_arr(
        "fog_per",
        VariableFloat,
        "Mixing coefficient for the fog each (sub)layer from 0.0 to 1.0.",
    )


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
        tw, th = mat.sample(self.width, self.height, with_offset=False)
        self.width = int(abs(tw))
        self.height = int(abs(th))

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
            nodes[i] = mat.sample(*pos)

    nodes = bind_prop_arr("nodes", VariableVec2)
    node_wait_times = bind_prop_arr("nodes_wait_time", VariableInt)
    puppet = bind_prop("puppet_id", VariableUInt, 0)


class CameraNodeType(IntEnum):
    """
    Enum defining the different camera node types
    """

    NORMAL = 1
    DETACH = 2
    CONNECT = 3
    INTEREST = 4
    FORCE_CONNECT = 5


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
        super().transform(mat)
        scale = mat.scale
        self.zoom = int(round(self.zoom * scale))
        self.width = int(round(self.width * scale))

    node_type = bind_prop(
        "node_type",
        VariableInt,
        CameraNodeType.NORMAL,
        "Camera node type, see :class:`CameraNodeType` enum.",
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
    door_set = bind_prop("door_set", VariableInt, 0)


class RedKeyDoor(Entity):
    """Red key door class"""

    TYPE_IDENTIFIER = "giga_gate"

    keys_needed = bind_prop("key_needed", VariableInt, 1)


class EntityHittable(Entity):
    """Base class for all 'hittable' types"""

    scale = bind_prop("dm_scale", VariableFloat, 1.0)

    def transform(self, mat: TxMatrix) -> None:
        """Adjust the entity scale"""
        super().transform(mat)
        self.scale = self.scale * mat.scale


class Enemy(EntityHittable):
    """Base class for all enemy types

    Subclasses can override :attr:`FILTH` to control how much "filth" is
    attributed to this entity. The DF file format requires a totalling of
    all filth in a level for completion calculations.
    """

    FILTH: int = 1


class EnemyLightPrism(Enemy):
    """Light prism entity class"""

    TYPE_IDENTIFIER = "enemy_tutorial_square"


class EnemyHeavyPrism(Enemy):
    """Heavy prism entity class. Note that although heavy prisms reward 3 dust
    when cleansing them they only count as 1 filth from the perspective of
    completion calculations."""

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

        self.lastX, self.lastY = mat.sample(self.lastX, self.lastY)

    door = bind_prop("door", VariableUInt, 0, "ID of door entity")
    lastX = bind_prop("lastKnowX", VariableFloat, 0.0)
    lastY = bind_prop("lastKnowY", VariableFloat, 0.0)


class EnemyDoor(Enemy):
    """Door entity class"""

    TYPE_IDENTIFIER = "enemy_door"

    FILTH = 0


class Apple(EntityHittable):
    """Apple entity class"""

    TYPE_IDENTIFIER = "hittable_apple"


class DustCharacter(EntityHittable):
    """Normal playable dust character entity types"""


class Dustman(DustCharacter):
    """Dustman entity class"""

    TYPE_IDENTIFIER = "dust_man"


class Dustgirl(DustCharacter):
    """Dustgirl entity classs"""

    TYPE_IDENTIFIER = "dust_girl"


class Dustkid(DustCharacter):
    """Dustkid entity class"""

    TYPE_IDENTIFIER = "dust_kid"


class Dustworth(DustCharacter):
    """Dustworth entity class"""

    TYPE_IDENTIFIER = "dust_worth"


class Dustwraith(DustCharacter):
    """Dustwraith entity class"""

    TYPE_IDENTIFIER = "dust_wraith"


class Leafsprite(DustCharacter):
    """Leaf sprite entity class"""

    TYPE_IDENTIFIER = "leaf_sprite"


class Trashking(DustCharacter):
    """Trash king entity class"""

    TYPE_IDENTIFIER = "trash_king"


class Slimeboss(DustCharacter):
    """Slime boss entity class"""

    TYPE_IDENTIFIER = "slime_boss"


class CustomScoreBook(Entity):
    """Custom score book (tome) entity class"""

    TYPE_IDENTIFIER = "custom_score_book"

    level_list = bind_prop("level_list_id", VariableInt, 0, "ID of StringList entity")


class StringList(Trigger):
    """Data container entity"""

    TYPE_IDENTIFIER = "z_string_list"

    data = bind_prop_arr("list", VariableString)


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
