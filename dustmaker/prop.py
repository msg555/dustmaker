""" Module containing dustmaker's prop representation.  """
import math

from .transform import TxMatrix


class Prop:
    """Class respresenting a static prop in a map.

    To find appropriate values for :attr:`prop_set`, :attr:`prop_group`, and
    :attr:`prop_index` check out
    https://github.com/cmann1/PropUtils/tree/master/files/prop_reference.

    Attributes:
        layer_sub (int): The sublayer the prop is rendered on. Note that the prop
            layer is actually stored within the containing
            :class:`dustmaker.level.Level` itself.
        rotation (16-bit uint): Clockwise rotation of the prop ranging from 0 to 0xFFFF.
            0x4000 corresponds to a 90 degree rotation, 0x8000 to 180 degrees, 0xC000
            to 270 degrees. This rotation is logically applied after any flips have
            been applied.
        flip_x (bool): Flip the prop horizontally
        flip_y (bool): Flip the prop vertically
        scale (float): Prop scaling factor. This is only available in `LevelType.DUSTMOD`
            type maps and is fairly coarse in the resolution of the scaling factor.
        prop_set (int): Identifier indicating what prop set this prop comes from. This
            appears to match :class:`dustmaker.tile.TileSpriteSet`.
        prop_group (int): Identifier indicating what prop group this prop comes from.
        prop_index (int): Index of the desired prop sprite.
        palette (int): The colour variant of the prop to render.
    """

    def __init__(
        self,
        layer_sub: int,
        rotation: int,
        flip_x: bool,
        flip_y: bool,
        scale: float,
        prop_set: int,
        prop_group: int,
        prop_index: int,
        palette: int,
    ) -> None:
        self.layer_sub = layer_sub
        self.rotation = rotation
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.scale = scale
        self.prop_set = prop_set
        self.prop_group = prop_group
        self.prop_index = prop_index
        self.palette = palette

    def transform(self, mat: TxMatrix) -> None:
        """
        Performs the requested transformation on the prop's :attr:`rotation` and
        :attr:`flip_y` attributes.
        """
        self.rotation = self.rotation - int(0x10000 * mat.angle / math.pi / 2) & 0xFFFF
        if mat.flipped:
            self.flip_y = not self.flip_y
            self.rotation = -self.rotation & 0xFFFF
