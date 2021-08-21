"""
Module defining the primary interface for working with levels in dustmaker.
"""
import copy
from enum import IntEnum
from typing import Dict, List, Optional, Tuple, TypeVar

from .entity import bind_prop, Entity
from .exceptions import LevelException
from .prop import Prop
from .tile import Tile
from .variable import Variable, VariableBool, VariableInt, VariableString

T = TypeVar("T")
TxMatrix = List[List[float]]


class LevelType(IntEnum):
    """Enum defining the different level types."""

    NORMAL = 0
    NEXUS = 1
    NEXUS_MP = 2
    KOTH = 3
    SURVIVAL = 4
    DUSTMOD = 6


class _LateBoundDescriptor:
    """Utility class to late bind a property descriptor to an instance"""

    def __init__(self, attrname: str, doc: str) -> None:
        self.attrname = attrname
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.attrname).__get__(obj, objtype)

    def __set__(self, obj, value):
        return getattr(obj, self.attrname).__set__(obj, value)

    def __delete__(self, obj):
        return getattr(obj, self.attrname).__delete__(obj)


class PlayerPosition:
    """Used internally to manage player position accessors. Meant to be used
    through accesss to :meth:`Level.start_position`."""

    def __init__(self, variables: Dict[str, Variable], player: int):
        self.variables = variables
        self._x = bind_prop(f"p{player}_x", VariableInt, 0)
        self._y = bind_prop(f"p{player}_y", VariableInt, 0)

    x = _LateBoundDescriptor("_x", "(int): Player start x-coordinate in pixels")
    y = _LateBoundDescriptor("_y", "(int): Player start y-coordinate in pixels")


class Level:
    """Represents a Dustforce level/map or the backdrop to its `parent` level. If
    this is a backdrop then :attr:`parent` will be set to the parent
    :class:`Level` object.

    Args:
        parent (:obj:`Level`, optional): If this level represents a backdrop this is the
            containing level. Typical usage should not need to use this parameter.

    Attributes:
        parent (Level, optional): For backdrops this is the containing level.
            Otherwise this is set to None.
        backdrop (Level, optional): The backdrop Level object or None if this is a
            backdrop level. Backdrop levels are scaled up 16x from the parent
            level's coordinate system and should only contain tiles and props.
        tiles (dict[(int, int, int), Tile]): A dict mapping (layer, x, y)
            to Tile objects.
        props (dict[int, (int, float, float, Prop)]): A dict mapping prop ids to
            (layer, x, y, Prop) tuples.
        entities (dict[int, (float, float, Entity)]): A dict mapping entity
            ids to (x, y, Entity) tuples. Ignored for backdrops.
        variables (dict[str, Variable]): A raw mapping of string keys to Variable objects.
            Some of these variables have nicer accessor properties like :attr:`name` but may
            be accessed raw through this dictionary. Ignored for backdrops.
        sshot (bytes): The level thumbnail image as a PNG binary. Ignored for
            backdrops.
    """

    def __init__(self, *, parent: Optional["Level"] = None) -> None:
        self._next_id = 100
        self.tiles: Dict[Tuple[int, int, int], Tile] = {}
        self.props: Dict[int, Tuple[int, float, float, Prop]] = {}
        self.variables: Dict[str, Variable] = {}

        self.parent = parent
        self.sshot = b""
        self.entities: Dict[int, Tuple[float, float, Entity]] = {}

        self.backdrop: Optional["Level"] = (
            Level(parent=self) if parent is None else None
        )
        self.dustmod_version = b"dustmaker"

    def _gen_id(self) -> int:
        """Allocate and return an ID for a new entity or prop."""
        if self.parent is not None:
            return self.parent._gen_id()
        result = self._next_id
        self._next_id += 1
        return result

    def _note_id(self, id_num: int) -> None:
        """Called to update the internally tracked minimum ID."""
        if self.parent is not None:
            self.parent._note_id(id_num)
        else:
            self._next_id = max(self._next_id, id_num + 1)

    name = bind_prop("level_name", VariableString, b"")
    virtual_character = bind_prop("vector_character", VariableBool, False)
    level_type = bind_prop(
        "level_type",
        VariableInt,
        LevelType.NORMAL,
        "level type of the level (see LevelType enum)",
    )
    dustmod_version = bind_prop("dustmod_version", VariableString, b"")

    def start_position(self, player: int = 1) -> PlayerPosition:
        """Returns a player position class that can access/modify the starting
        position of each player.

        Args:
            player (int, optional): The player to access the starting position
                of. Valid options are 1, 2, 3, 4. Defaults to player 1.
        """
        return PlayerPosition(self.variables, player)

    def add_prop(
        self, layer: int, x: float, y: float, prop: Prop, id_num: Optional[int] = None
    ) -> int:
        """Adds a new :class:`Prop` to the level and returns its id. This is the
        preferred way of adding props to a level. Do not directly add props to the
        :attr:`props` attribute and use this method as it may overwrite props.

        Args:
            x (float): The x position of the prop.
            y (float): The y position of the prop.
            prop (Prop): The Prop object to add to the level.
            id_num: (int, optional): The prop identifier. If not set the identifier
                will be allocated for you.

        Returns:
            The ID of the newly added prop.

        Raises:
            LevelException: If the given ID is already in use.
        """
        if id_num is None:
            id_num = self._gen_id()
        else:
            self._note_id(id_num)
        if id_num in self.props:
            raise LevelException("level already has prop id")
        self.props[id_num] = (layer, x, y, prop)
        return id_num

    def add_entity(
        self, x: float, y: float, entity: Entity, id_num: Optional[int] = None
    ) -> int:
        """Adds a new :class:`Entity` to the level and returns its id. This is the
        preferred way of adding entities to a level. Do not directly add entities to the
        :attr:`entities` attribute and use this method as it may overwrite entities.

        Args:
            x (float): The x position of the entity.
            y (float): The y position of the entity.
            entity (Entity): The Entity object to add to the level.
            id_num: (int, optional): The entity identifier. If not set the
                identifier will be allocated for you.

        Returns:
            The ID of the newly added entity.

        Raises:
            LevelException: If the given ID is already in use.
        """
        if id_num is None:
            id_num = self._gen_id()
        else:
            self._note_id(id_num)

        if id_num in self.entities:
            raise LevelException("level already has entity with ID")
        self.entities[id_num] = (x, y, entity)
        return id_num

    def translate(self, x: float, y: float) -> None:
        """Translate (move) the entire level.  This is just a convenience method
        around :meth:`transform`.

        Args:
            x (float): The number of pixels to move horizontally.
            y (float): The number of pixels to move vertically.
        """
        self.transform([[1, 0, x], [0, 1, y], [0, 0, 1]])

    def remap_ids(self, min_id: int = 100) -> None:
        """Remap prop and entity ids starting at `min_id`. This is useful
        when attempting to merge two levels to keep their ID space separate.
        Do not call directly on a backdrop level.

        Args:
            min_id (int, optional): The minimum ID to assign to a prop or entity.
        """
        self._next_id = min_id

        prop_remap = {id_num: self._gen_id() for id_num in self.props}
        self.props = {prop_remap[id_num]: prop for id_num, prop in self.props.items()}

        entity_remap = {id_num: self._gen_id() for id_num in self.entities}
        self.entities = {
            entity_remap[id_num]: entity for id_num, entity in self.entities.items()
        }
        for _, _, entity in self.entities.values():
            entity.remap_ids(entity_remap)

        if self.backdrop is not None:
            self.backdrop.remap_ids()

    def calculate_max_id(self, reset: bool = True) -> int:
        """Calculates the maximum prop or entity ID currently in use. This will
        always return at least 100 due to Dustforce reserving many of the lower
        IDs for special entities like the camera.

        Arguments:
            reset (bool, optional): If set (the default) the internal next ID
                allocator will be reset based off this result. Otherwise the max
                ID will be at least one less than the next ID.
        """
        init = 100 if reset else self._next_id - 1
        mx_id = max(max(self.props, default=init), max(self.entities, default=init))
        if self.backdrop is not None:
            mx_id = max(mx_id, self.backdrop.calculate_max_id())
        self._next_id = mx_id + 1
        return mx_id

    def merge(self, other_level: "Level", remap_ids: bool = True) -> None:
        """Merge another level into this one.

        Args:
            other_map (Level): The level to merge into this one.
            remap_ids (bool, optional): Wether to remap the ID space of each
                level so they do not interfere with each other. This is True by
                default.
        """
        if remap_ids:
            self.remap_ids(other_level.calculate_max_id() + 1)

        self.tiles.update(copy.deepcopy(other_level.tiles))
        self.props.update(copy.deepcopy(other_level.props))
        self.entities.update(copy.deepcopy(other_level.entities))
        if self.backdrop is not None and other_level.backdrop is not None:
            self.backdrop.merge(other_level.backdrop, remap_ids=False)

    def transform(self, mat: TxMatrix) -> None:
        """Transforms the level with the given affine transformation matrix.  Note
        that this will probably not produce desirable results if the
        transformation matrix is not some mixture of a translation, flip,
        and 90 degree rotations. Use :meth:`upscale` if you wish to performan
        an upscale as well as a transformation.

        In most cases you can use one of :meth:`flip_horizontal`,
        :meth:`flip_vertical:, :meth:`rotate`, :meth:`translate`, :meth:`upscale`
        instead of this method.

        Args:
            mat: The 3 by 3 affine transformation matrix [x', y', 1]' = mat *
                [x, y, 1]'. It should be of the form
                `mat = [[xx, xy, ox], [yx, yy, oy], [0, 0, 1]]`.
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
        """Flips the level horizontally. This is a convenience function around
        :meth:`transform`."""
        self.transform([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])

    def flip_vertical(self) -> None:
        """Flips the level vertically. This is a convenience function around
        :meth:`transform`."""
        self.transform([[1, 0, 0], [0, -1, 0], [0, 0, 1]])

    def rotate(self, times: int = 1) -> None:
        """Rotates the level 90 degrees clockwise. This is a convenience function
        around :meth:`transform`.

        Args:
            times (int, optional): The number of 90 degree clockwise rotations
                to perform. `times` may be negative to perform counterclockwise
                rotations.
        """
        cs = [1, 0, -1, 0]
        sn = [0, 1, 0, -1]
        times %= 4
        self.transform(
            [[cs[times], -sn[times], 0], [sn[times], cs[times], 0], [0, 0, 1]]
        )

    def upscale(self, factor: int, *, mat: Optional[TxMatrix] = None) -> None:
        """Increase the size of the level along each axis.

        Args:
            factor (int): The scaling factor (>1). e.g. if `factor` = 2 each tile
                tile will be represented by a 2x2 tile squre in the resulting
                level.
            mat (optional): An additional transformation matrix to pass
                to :meth:`transform` along with the upscaling.
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
