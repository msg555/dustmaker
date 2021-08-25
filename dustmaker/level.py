"""
Module defining the primary interface for working with levels in dustmaker.
"""
import copy
from enum import IntEnum
import functools
import math
from typing import Callable, Dict, Optional, Tuple, TypeVar

from .entity import bind_prop, Entity
from .exceptions import LevelException
from .prop import Prop
from .tile import (
    Tile,
    TileEdgeData,
    TileShape,
    TileSide,
    TileSpriteSet,
    SHAPE_VERTEXES,
    SIDE_CLOCKWISE_INDEX,
)
from .transform import TxMatrix
from .variable import Variable, VariableBool, VariableInt, VariableString

T = TypeVar("T")


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

    x = _LateBoundDescriptor("_x", "int: Player start x-coordinate in pixels")
    y = _LateBoundDescriptor("_y", "int: Player start y-coordinate in pixels")


class Level:
    """Represents a Dustforce level/map or the backdrop to its `parent` level. If
    this is a backdrop then :attr:`parent` will be set to the parent
    :class:`Level` object.

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
        "Level type of the level, see :class:`LevelType` enum.",
    )
    dustmod_version = bind_prop("dustmod_version", VariableString, b"")

    def start_position(self, player: int = 1) -> PlayerPosition:
        """Access and modify the starting position of each player.

        Args:
            player (int, optional): The player to access the starting position
                of. Valid options are 1, 2, 3, 4. Defaults to player 1.

        Returns:
            An accessor class with `x` and `y` attributes that can be get/set.
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
        self.transform(TxMatrix.IDENTITY.translate(x, y))

    def remap_ids(self, min_id: int = 100) -> None:
        """Remap prop and entity ids starting at `min_id`. This is useful
        when attempting to merge two levels to keep their ID space separate.
        Do not call directly on a backdrop level.

        Args:
            min_id (int, optional): The minimum ID to assign to a prop or entity.

        Warning:
            Dustmaker has no way to automatically remap entity IDs in script persist data.
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

        Warning:
            Dustmaker has no way to automatically transform positional data in
            script persist data.
        """

        def _transform_tiles():
            for (layer, x, y), tile in self.tiles.items():
                tile.transform(mat)
                tx, ty = mat.sample(x * 48, y * 48)

                yield (layer, int(round(tx / 48.0)), int(round(ty / 48.0))), tile

        def _transform_props():
            for id_num, (layer, x, y, prop) in self.props.items():
                prop.transform(mat)
                tx, ty = mat.sample(x, y)
                yield id_num, (layer, tx, ty, prop)

        def _transform_entities():
            for id_num, (x, y, entity) in self.entities.items():
                entity.transform(mat)
                tx, ty = mat.sample(x, y)
                yield id_num, (tx, ty, entity)

        self.tiles = dict(_transform_tiles())
        self.props = dict(_transform_props())
        self.entities = dict(_transform_entities())

        for player in range(1, 5):
            pos = self.start_position(player)
            pos_tx, pos_ty = mat.sample(pos.x, pos.y)
            pos.x, pos.y = int(round(pos_tx)), int(round(pos_ty))

        if self.backdrop is not None:
            self.backdrop.transform(mat)

    def flip_horizontal(self) -> None:
        """Flips the level horizontally. This is a convenience function around
        :meth:`transform`."""
        self.transform(TxMatrix.HFLIP)

    def flip_vertical(self) -> None:
        """Flips the level vertically. This is a convenience function around
        :meth:`transform`."""
        self.transform(TxMatrix.VFLIP)

    def rotate(self, times: int = 1) -> None:
        """Rotates the level 90 degrees clockwise. This is a convenience function
        around :meth:`transform`.

        Args:
            times (int, optional): The number of 90 degree clockwise rotations
                to perform. `times` may be negative to perform counterclockwise
                rotations.
        """
        self.transform(TxMatrix.ROTATE[times % 4])

    def upscale(self, factor: int, *, mat: TxMatrix = TxMatrix.IDENTITY) -> None:
        """Increase the size of the level along each axis.

        Args:
            factor (int): The scaling factor (>1). e.g. if `factor` = 2 each tile
                tile will be represented by a 2x2 tile squre in the resulting
                level.
            mat (optional): An additional transformation matrix to pass
                to :meth:`transform` along with the upscaling.
        """
        self.transform(mat * factor)
        self.tiles = {
            (layer, x + dx, y + dy): ntile
            for (layer, x, y), tile in self.tiles.items()
            for dx, dy, ntile in tile.upscale(factor)
        }

    def calculate_edge_visibility(
        self,
        *,
        visible_callback: Optional[
            Callable[[int, int, TileSide, Tile, Tile], bool]
        ] = None,
    ) -> None:
        """This method will automatically calculate edge solidity and
        visibility in a way meant to match Dustforce rules.

        Solidity will always imply visibility. An edge that doesn't exist
        for the given tile shape is always not visible. Otherwise an edge
        that is not flush to a
        tile border (e.g. the diagonal of a slope tile) is solid. Otherwise
        if the neighboring side does not exist or is not also flush the
        edge is solid.

        In any other case the edge is not solid. If the tile sprite information
        matches its neighbor the edge is not visible. Otherwise
        `visible_callback` is called to determine if the edge is visible. If
        `visible_callback` is not set this defaults to the edge being visible
        if it's a bototm or right edge.
        bottom or right edge.

        Arguments:
            visible_callback (Callable): Callback used to determine if a given
                edge should be visible if all other checks have passed. Typically
                this function should be anti-symetric so that there are not
                overlapping visible edges. Called as
                `visible_callback(x, y, side, tile, neighbor_tile)`.
        """
        neighbor_dir = ((0, -1), (0, 1), (-1, 0), (1, 0))

        @functools.lru_cache(maxsize=None)
        def _check_edge(shape: TileShape, side: TileSide) -> Tuple[bool, bool]:
            """Gets properties of a given edge for a given shape.

            Returns:
                (exists: bool, flush: bool)
            """
            ind = SIDE_CLOCKWISE_INDEX[side]
            vert_a = SHAPE_VERTEXES[shape][ind]
            vert_b = SHAPE_VERTEXES[shape][(ind + 1) & 0x3]

            if abs(vert_a[0] - vert_b[0]) + abs(vert_a[1] - vert_b[1]) <= 1:
                return False, False
            return True, vert_a[0] == vert_b[0] or vert_a[1] == vert_b[1]

        for (layer, x, y), tile in self.tiles.items():
            for side in TileSide:
                edge_exists, edge_flush = _check_edge(tile.shape, side)

                if not edge_exists:
                    tile.edge_data[side] = TileEdgeData()
                    continue

                edat = tile.edge_data[side]
                if not edge_flush:
                    edat.solid = edat.visible = True
                    continue

                # Flush edge, check if neighbor is flush too
                ndir = neighbor_dir[side]
                ntile = self.tiles.get((layer, x + ndir[0], y + ndir[1]))

                if ntile is None:
                    edat.solid = edat.visible = True
                    continue

                nedge_exists, nedge_flush = _check_edge(ntile.shape, side ^ 1)
                if not nedge_exists or not nedge_flush:
                    edat.solid = edat.visible = True
                    continue

                edat.solid = False
                if (tile.sprite_set, tile.sprite_tile, tile.sprite_palette) == (
                    ntile.sprite_set,
                    ntile.sprite_tile,
                    ntile.sprite_palette,
                ):
                    edat.visible = False
                elif visible_callback is None:
                    edat.visible = side in (TileSide.BOTTOM, TileSide.RIGHT)
                else:
                    edat.visible = visible_callback(x, y, side, tile, ntile)

    def calculate_edge_caps(self) -> None:
        """Calculates edge/filth cap flags and angles. This should be called
        after all edge visibilty has been determined (see
        :meth:`calculate_edge_visibility`).

        To compute edge caps we consider only visible edges. Non-visible
        edges will have their cap data appropriately zeroed. For each
        visible edge we consider it in both orientations; going clockwise
        and counter-clockwise around the tile.

        Edges that end between tile widths (i.e. for the slant edge of a
        slant) can never have an edge cap. For these edges the edge/filth cap
        should be set to False and the angles zeroed.

        The first step to computing the cap flag and angle for a given edge
        orientation is to find the "joining" edge. A joining edge must have
        the following properties:

        * Belong to a tile with the same sprite
        * Be the same side of the tile (i.e. ground edges don't connect to walls)
        * Have a starting point equal to our edge's ending point
        * Be in the same orientation as our edge

        If there are multiple joining edges the one that moves the most "away"
        from our tile should be selected (when traversing clockwise the edge
        that goes the most counter-clockwise and vice versa).

        If there is no joining edge the edge cap should be set to True and
        the edge angle should be zeroed. If there is a joining edge the edge
        cap should be set to False and the edge angle should be half the angle
        delta rounded down. Clockwise turns should be positive,
        counter-clockwise turns should be negative.

        Finally if the edge has no filth then the filth cap and angle should be
        zeroed. If there is filth on this edge but not the joining edge, or the
        filth sprites/spike types don't match, the filth cap should be set to
        True and filth angle to 0. Otherwise the filth cap should be False and
        the filth angle should match the edge angle.
        """
        for (layer, x, y), tile in self.tiles.items():
            for side, edge_data in zip(TileSide, tile.edge_data):
                if not edge_data.visible:
                    # Clear all invalid data for invisible tiles.
                    edge_data.caps = (False, False)
                    edge_data.angles = (0, 0)
                    edge_data.filth_caps = (False, False)
                    edge_data.filth_angles = (0, 0)
                    edge_data.filth_sprite_set = TileSpriteSet.NONE_0
                    edge_data.filth_spike = False
                    continue

                # Use temporarily mutable locals to write results
                caps = [False, False]
                angles = [0, 0]
                filth_caps = [False, False]
                filth_angles = [0, 0]

                for dr in range(2):
                    cw_ind = SIDE_CLOCKWISE_INDEX[side]
                    vert_a = SHAPE_VERTEXES[tile.shape][(cw_ind + 1 - dr) & 0x3]
                    vert_b = SHAPE_VERTEXES[tile.shape][(cw_ind + dr) & 0x3]

                    ddirs: Tuple[Tuple[int, int], ...] = ()
                    if vert_b == (0, 0):
                        ddirs = ((-1, 0), (-1, -1), (0, -1))
                    elif vert_b == (2, 0):
                        ddirs = ((0, -1), (1, -1), (1, 0))
                    elif vert_b == (2, 2):
                        ddirs = ((1, 0), (1, 1), (0, 1))
                    elif vert_b == (0, 2):
                        ddirs = ((0, 1), (-1, 1), (-1, 0))
                    else:  # Slants
                        # No caps allowed on slant half edges
                        continue
                    if dr:
                        ddirs = ddirs[::-1]

                    for dx, dy in ddirs:
                        ntile = self.tiles.get((layer, x + dx, y + dy))
                        if (
                            ntile is None
                            or tile.get_sprite_tuple() != ntile.get_sprite_tuple()
                        ):
                            continue

                        nedge_data = ntile.edge_data[side]
                        if not nedge_data.visible:
                            continue

                        nvert_a = SHAPE_VERTEXES[ntile.shape][(cw_ind + 1 - dr) & 0x3]
                        nvert_b = SHAPE_VERTEXES[ntile.shape][(cw_ind + dr) & 0x3]
                        nvert_a = (nvert_a[0] + dx * 2, nvert_a[1] + dy * 2)
                        nvert_b = (nvert_b[0] + dx * 2, nvert_b[1] + dy * 2)
                        if vert_b == nvert_a:
                            break
                    else:
                        # No joiner
                        caps[dr] = True
                        angles[dr] = 0
                        filth_caps[dr] = bool(edge_data.filth_sprite_set)
                        filth_angles[dr] = 0
                        continue

                    delta_angle = (
                        math.atan2(vert_b[1] - vert_a[1], vert_b[0] - vert_a[0])
                        - math.atan2(nvert_b[1] - nvert_a[1], nvert_b[0] - nvert_a[0])
                    ) % (2 * math.pi)
                    if delta_angle > math.pi:
                        delta_angle -= 2 * math.pi

                    angle = -int(round(delta_angle * 180 / math.pi / 2))

                    # Set caps and angles based on joiner
                    caps[dr] = False
                    angles[dr] = angle
                    filth_angles[dr] = 0
                    filth_caps[dr] = False
                    if edge_data.filth_sprite_set:
                        # pylint: disable=undefined-loop-variable
                        if (edge_data.filth_spike, edge_data.filth_sprite_set) == (
                            nedge_data.filth_spike,
                            nedge_data.filth_sprite_set,
                        ):
                            filth_angles[dr] = angle
                        else:
                            filth_caps[dr] = True

                edge_data.caps = tuple(caps)  # type: ignore
                edge_data.angles = tuple(angles)  # type: ignore
                edge_data.filth_caps = tuple(filth_caps)  # type: ignore
                edge_data.filth_angles = tuple(filth_angles)  # type: ignore
