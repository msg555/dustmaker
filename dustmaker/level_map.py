"""
Module defining the primary interface for working with maps in dustmaker.
"""
import copy
from typing import Dict, List, Optional, Tuple, TypeVar

from .entity import bind_prop, Entity
from .enums import LevelType
from .map_exception import MapException
from .prop import Prop
from .tile import Tile
from .variable import Variable, VariableBool, VariableInt, VariableString

T = TypeVar("T")
TxMatrix = List[List[float]]


class _LateBoundDescriptor:
    """Utility class to late bind a property descriptor to an instance"""

    def __init__(self, attrname: str) -> None:
        self.attrname = attrname

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.attrname).__get__(obj, objtype)

    def __set__(self, obj, value):
        return getattr(obj, self.attrname).__set__(obj, value)

    def __delete__(self, obj):
        return getattr(obj, self.attrname).__delete__(obj)


class _PlayerPosition:
    """Used internally to manage player position accessors"""

    def __init__(self, variables: Dict[str, Variable], player: int):
        self.variables = variables
        self._x = bind_prop(f"p{player}_x", VariableInt, 0)
        self._y = bind_prop(f"p{player}_y", VariableInt, 0)

    x = _LateBoundDescriptor("_x")
    y = _LateBoundDescriptor("_y")


class Map:
    """Represents a Dustforce level.

    A map contains the following attributes:

    map.tiles - A dict mapping (layer, x, y) to Tile objects.
    map.props - A dict mapping prop ids to (layer, x, y, Prop) tuples.
    map.parent - For backdrops this is the containing map.  Otherwise this is
                 set to None.

    If the map is not a backdrop (i.e. map.parent == None) then the following
    attributes will also be available (for backdrops they will exist but be
    ignored)

    map.entities - A dict mapping entity ids to (x, y, Entity) tuples.
    map.backdrop - The backdrop Map object.  Backdrop maps can only contain
                   tiles and props and each tile is the size of 16 tiles in
                   the top level coordinate system.
    map.variables - A raw mapping of string keys to Variable objects.  Some of these
                    variables have nicer accessors like map.name(...).
    map.sshot - The level thumbnail image.  This appears to be a PNG image
                 with some custom or missing header.
    """

    def __init__(self, *, parent: Optional["Map"] = None) -> None:
        """Constructs a blank level object.

        parent - If this Map represents a backdrop this is the containing map.
                 Typical usage should not need to use this parameter.
        """
        self._min_id = 100
        self.tiles: Dict[Tuple[int, int, int], Tile] = {}
        self.props: Dict[int, Tuple[int, float, float, Prop]] = {}
        self.variables: Dict[str, Variable] = {}

        self.parent = parent
        self.sshot = b""
        self.entities: Dict[int, Tuple[float, float, Entity]] = {}

        self.backdrop: Optional["Map"] = Map(parent=self) if parent is None else None
        self.dustmod_version = b"dustmaker"

    def _next_id(self) -> int:
        """Allocate and return an ID for a new entity or prop."""
        if self.parent is not None:
            return self.parent._next_id()
        result = self._min_id
        self._min_id += 1
        return result

    def _note_id(self, id_num) -> None:
        """Called to update the internally tracked minimum ID."""
        if self.parent is not None:
            self.parent._note_id(id_num)
        else:
            self._min_id = max(self._min_id, id_num + 1)

    name = bind_prop("level_name", VariableString, b"")
    virtual_character = bind_prop("vector_character", VariableBool, False)
    level_type = bind_prop(
        "level_type",
        VariableInt,
        LevelType.NORMAL,
        "level type of the map (see LevelType enum)",
    )
    dustmod_version = bind_prop("dustmod_version", VariableString, b"")

    def start_position(self, player: int = 1) -> "_PlayerPosition":
        """Returns a player position class that can access/modify the position
        through 'x' and 'y' properties"""
        return _PlayerPosition(self.variables, player)

    def add_prop(
        self, layer: int, x: float, y: float, prop: Prop, id_num: Optional[int] = None
    ) -> int:
        """Adds a new prop to the map and returns its id.

        x - The x position in tile units of the prop.
        y - The y position in tile units of the prop.
        prop - The Prop object to add to the map.
        id_num - The prop identifier.  If set to None the identifier will be
             allocated for you.

        Raises a MapException if the given id is already in use.
        """
        if id_num is None:
            id_num = self._next_id()
        else:
            self._note_id(id_num)
        if id_num in self.props:
            raise MapException("map already has prop id")
        self.props[id_num] = (layer, x, y, prop)
        return id_num

    def add_entity(
        self, x: float, y: float, entity: Entity, id_num: Optional[int] = None
    ) -> int:
        """Adds a new entity to the map and returns its id.

        x - The x position in tile units of the entity.
        y - The y position in tile units of the entity.
        entity - The Entity object to add to the map.
        id_num - The entity identifier.  If set to None the identifier will be
             allocated for you.

        Raises a MapException if the given id is already in use.
        """
        if id_num is None:
            id_num = self._next_id()
        else:
            self._note_id(id_num)

        if id_num in self.entities:
            raise MapException("map already has id")
        self.entities[id_num] = (x, y, entity)
        return id_num

    def translate(self, x: float, y: float) -> None:
        """Translate the entire map x pixels laterally and y pixels horizontally.

        x - The number of pixels to move laterally.
        y - The number of pixels to move horizontally.
        """
        self.transform([[1, 0, x], [0, 1, y], [0, 0, 1]])

    def remap_ids(self, min_id: Optional[int] = None):
        """Remap prop and entity ids starting at min_id.

        This calls through to all entities to remap any references to other
        entity ids.
        """
        if min_id is None:
            self._min_id = 100
        else:
            self._min_id = min_id

        prop_remap = {id_num: self._next_id() for id_num in self.props}
        self.props = {prop_remap[id_num]: prop for id_num, prop in self.props.items()}

        entity_remap = {id_num: self._next_id() for id_num in self.entities}
        self.entities = {
            entity_remap[id_num]: entity for id_num, entity in self.entities.items()
        }
        for (_, _, entity) in self.entities.values():
            entity.remap_ids(entity_remap)

        if self.backdrop is not None:
            self.backdrop.remap_ids()

    def merge_map(self, other_map, _do_remap_ids=True):
        """Merge a map into this one.

        map - The Map to merge into this one.
        """
        if _do_remap_ids:
            self.remap_ids(other_map._min_id)
        self.tiles.update(copy.deepcopy(other_map.tiles))
        self.props.update(copy.deepcopy(other_map.props))

        if hasattr(self, "backdrop") and hasattr(other_map, "backdrop"):
            self.entities.update(copy.deepcopy(other_map.entities))
            self.backdrop.merge_map(other_map.backdrop, False)

    def transform(self, mat: TxMatrix) -> None:
        """Transforms the map with the given affine transformation matrix.  Note
        that this will probably not produce desirable results if the
        transformation matrix is not some mixture of a translation, flip,
        and 90 degree rotations.

        In most cases you should not use this method directly and instead use
        Map.flip_horizontal(), Map.flip_vertical(), or Map.rotate().

        mat - The affine transformation matrix. [x', y', 1]' = mat * [x, y, 1]'
        """
        self.tiles = {
            (
                layer,
                int(
                    round(
                        mat[0][2] / 48.0
                        + x * mat[0][0]
                        + y * mat[0][1]
                        + min(0, mat[0][0])
                        + min(0, mat[0][1])
                    )
                ),
                int(
                    round(
                        mat[1][2] / 48.0
                        + x * mat[1][0]
                        + y * mat[1][1]
                        + min(0, mat[1][0])
                        + min(0, mat[1][1])
                    )
                ),
            ): tile
            for (layer, x, y), tile in self.tiles.items()
        }
        self.props = {
            id_num: (
                layer,
                mat[0][2] + x * mat[0][0] + y * mat[0][1],
                mat[1][2] + x * mat[1][0] + y * mat[1][1],
                prop,
            )
            for id_num, (layer, x, y, prop) in self.props.items()
        }
        for tile in self.tiles.values():
            tile.transform(mat)
        for _, _, _, prop in self.props.values():
            prop.transform(mat)

        for player in range(1, 5):
            pos = self.start_position(player)
            pos.x, pos.y = (
                int(round(mat[0][2] + pos.x * mat[0][0] + pos.y * mat[0][1])),
                int(round(mat[1][2] + pos.x * mat[1][0] + pos.y * mat[1][1])),
            )

        self.entities = {
            id_num: (
                mat[0][2] + x * mat[0][0] + y * mat[0][1],
                mat[1][2] + x * mat[1][0] + y * mat[1][1],
                entity,
            )
            for id_num, (x, y, entity) in self.entities.items()
        }
        for _, _, entity in self.entities.values():
            entity.transform(mat)

        if self.backdrop is not None:
            self.backdrop.transform(mat)

    def flip_horizontal(self) -> None:
        """Flips the map horizontally."""
        self.transform([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])

    def flip_vertical(self) -> None:
        """Flips the map vertically."""
        self.transform([[1, 0, 0], [0, -1, 0], [0, 0, 1]])

    def rotate(self, times: int = 1) -> None:
        """Rotates the map 90 degrees `times` times.

        times - The number of 90 degree rotations to perform.  This can be negative.
        """
        cs = [1, 0, -1, 0]
        sn = [0, 1, 0, -1]
        times %= 4
        self.transform(
            [[cs[times], -sn[times], 0], [sn[times], cs[times], 0], [0, 0, 1]]
        )

    def upscale(self, factor: int, *, mat: Optional[TxMatrix] = None) -> None:
        """Increase the size of the map along each axis by `factor`.

        mat - Optionally apply an additional transform. The transform will be
              applied logically after the upscale.
        """
        if mat is None:
            self.transform([[factor, 0, 0], [0, factor, 0], [0, 0, 1]])
        else:
            self.transform(
                [
                    [
                        val * (factor if col < 2 else 1)
                        for col, val in enumerate(mat_row)
                    ]
                    for mat_row in mat
                ]
            )

        self.tiles = {
            (layer, x + dx, y + dy): ntile
            for (layer, x, y), tile in self.tiles.items()
            for dx, dy, ntile in tile.upscale(factor)
        }
