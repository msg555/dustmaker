"""
Module defining the replay container types
"""
import dataclasses
from enum import IntEnum, IntFlag
from typing import Any, Callable, Dict, List, Optional

#: Latest replay version supported by dustmaker/dustmod
LATEST_VERSION = 4


class IntentStream(IntEnum):
    """Enumeration of the different intent streams in the order they
    are listed within the replay binary format.
    """

    #: X intent: -1 for left, 0 for neutral, 1 for right
    X = 0
    #: Y intent: -1 for up, 0 for nuetral, 1 for down
    Y = 1
    #: jump intent: 0 for not pressed, 1 for pressed and unused, 2 for pressed
    #: and used.
    JUMP = 2
    #: dash intent: 0 for not pressed, 1 for pressed and unused, 2 for pressed
    #: and used (2 is only present for weird subframe things).
    DASH = 3
    #: fall intent: 0 for not pressed, 1 for pressed and unused, 2 for pressed
    #: and used (2 is only present for weird subframe things).
    FALL = 4
    #: light intent: 0 for not pressed, 10 for pressed and unused, 11 for pressed
    #: and used, 1-9 counts down from 10 after the key is released and unused,
    #: during this time the intent will be consumed if possible from the player
    #: state.
    LIGHT = 5
    #: heavy intent: 0 for not pressed, 10 for pressed and unused, 11 for pressed
    #: and used, 1-9 counts down from 10 after the key is released and unused,
    #: during this time the intent will be consumed if possible from the player
    #: state.
    HEAVY = 6
    #: taunt intent: 0 for not pressed, 1 for pressed and unused, 2 for pressed
    #: and used.
    TAUNT = 7
    #: mouse x: float in the range [0.0, 1.0] where 0.0 corresponds to the left of
    #: the screen and 1.0 corresponds to the right of the screen. This is internally
    #: stored with 16 bits of accuracy.
    MOUSE_X = 8
    #: mouse y: float in the range [0.0, 1.0] where 0.0 corresponds to the top of
    #: the screen and 1.0 corresponds to the bottom of the screen. This is internally
    #: stored with 16 bits of accuracy.
    MOUSE_Y = 9
    #: mouse state: bit mask of current mouse state as defined in :class:`MouseState`.
    MOUSE_STATE = 10


class MouseState(IntFlag):
    """Mouse state bitmask values associated with the
    :attr:`IntentStream.MOUSE_STATE` intent.
    """

    WHEEL_UP = 1
    WHEEL_DOWN = 2
    LEFT_CLICK = 4
    RIGHT_CLICK = 8
    MIDDLE_CLICK = 16


class Character(IntEnum):
    """Numeric character IDs for each playable character"""

    DUSTMAN = 0
    DUSTGIRL = 1
    DUSTKID = 2
    DUSTWORTH = 3
    SLIMEBOSS = 4
    TRASHKING = 5
    LEAFSPRITE = 6
    DUSTWRAITH = 7


@dataclasses.dataclass
class _IntentMetadata:
    """Container class for metadata about an intent stream"""

    bits: int
    version: int = 1
    to_repr: Callable[[int], Any] = lambda x: x
    to_bits: Callable[[Any], int] = lambda x: x
    default: Any = 0


_INTENT_META = (
    _IntentMetadata(
        bits=2,
        to_repr=lambda x: x - 1,
        to_bits=lambda x: x + 1,
    ),  # X
    _IntentMetadata(
        bits=2,
        to_repr=lambda x: x - 1,
        to_bits=lambda x: x + 1,
    ),  # Y
    _IntentMetadata(bits=2),  # JUMP
    _IntentMetadata(bits=2),  # DASH
    _IntentMetadata(bits=2),  # FALL
    _IntentMetadata(bits=4),  # LIGHT
    _IntentMetadata(bits=4),  # HEAVY
    _IntentMetadata(
        bits=4,
        version=3,
    ),  # TAUNT
    _IntentMetadata(
        bits=16,
        to_repr=lambda x: x / 32767.0,
        to_bits=lambda x: int(round(x * 32767)),
        version=4,
        default=0.0,
    ),  # MOUSE_X
    _IntentMetadata(
        bits=16,
        to_repr=lambda x: x / 32767.0,
        to_bits=lambda x: int(round(x * 32767)),
        version=4,
        default=0.0,
    ),  # MOUSE_Y
    _IntentMetadata(
        bits=8,
        to_repr=MouseState,
        to_bits=int,
        version=4,
        default=MouseState(0),
    ),  # MOUSE_STATE
)


@dataclasses.dataclass
class PlayerData:
    """Container class for a single player's replay data"""

    character: Character = Character.DUSTMAN
    #: The intent data parsed from the replay file. These may have length
    #: smaller than the number of frames in the replay in which case
    #: the neutral value for that intent should be considered the active intent
    #: on those frames. Use `:meth:`get_intent_value` to automatically deal
    #: with this when reading replays.
    intents: Dict[IntentStream, List[Any]] = dataclasses.field(default_factory=dict)

    def get_intent_value(self, intent: IntentStream, frame: int) -> Any:
        """Returns the value for the given intent at the given frame"""
        values = self.intents.get(intent)
        if values is None or not (0 <= frame < len(values)):
            return _INTENT_META[intent].default
        return values[frame]


@dataclasses.dataclass
class EntityFrame:
    """Container class for a single frame worth of entity desync data."""

    #: Frame timer for this entity frame.
    frame: int = 0
    #: X position of the entity. This has a resolution of a tenth of a pixel.
    x_pos: float = 0.0
    #: Y position of the entity. This has a resolution of a tenth of a pixel.
    y_pos: float = 0.0
    #: X-speed of the entity. This has a resolution of 0.01 pixels/s.
    x_speed: float = 0.0
    #: Y-speed of the entity. This has a resolution of 0.01 pixels/s.
    y_speed: float = 0.0


@dataclasses.dataclass
class EntityData:
    """Container class for all the desync frame data for an entity. Note that
    the engine only stores desync data every 8 frames (and then slower than that
    eventually for long replays) and only stores the data if the entity moved
    significantly.
    """

    #: Frame data for the given entity. This should appear in increasing order
    #: of frame time but the times might not increase at the same rate.
    frames: List[EntityFrame] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Replay:
    """Container class for a replay"""

    #: The format of the replay file. If writing a replay just use
    #: LATEST_VERSION unless you want compatibility with vanilla.
    version: int = LATEST_VERSION
    #: The username associated with the replay. If this is unset no
    #: username header will be included. If feeding the replay binary
    #: directly to dustmod make sure to include a username as it does
    #: expect to find a replay header.
    username: bytes = b""
    #: The level filename associated with the replay.
    level: bytes = b""
    #: The length of the replay in frames.
    frames: int = 0
    #: Per-player replay data
    players: List[PlayerData] = dataclasses.field(default_factory=list)
    #: Entity desync data per entity. This maps the entity ID in the map to
    #: EntityData captured for that entity. Camera entities get the special
    #: ID of 1 + 2 * player_index and player entities get the special
    #: ID of 2 * player_index (alternatively you can use :meth:`get_camera_entity_data`
    #: :meth:`get_player_entity_data` to access these data).
    entities: Dict[int, EntityData] = dataclasses.field(default_factory=dict)

    def get_player_entity_data(self, player: int = 1) -> Optional[EntityData]:
        """Get the entity data for the given player entity.

        Args:
            player (int, optional): The player to get the entity data for indexed from 1
        """
        return self.entities.get(2 * player)

    def get_camera_entity_data(self, player: int = 1) -> Optional[EntityData]:
        """Get the entity data for the camera following the given player.

        Args:
            player (int, optional): The player to get the camera of indexed from 1
        """
        return self.entities.get(1 + 2 * player)
