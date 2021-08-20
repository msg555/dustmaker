"""
Module containing dustmaker's prop representation
"""
import math
from typing import List

TxMatrix = List[List[float]]


class Prop:
    """
    Class respresenting a static prop in a map.
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
        Performs the requested transformation on the prop's position/scaling.
        """
        angle = math.atan2(mat[1][1], mat[1][0]) - math.pi / 2
        self.rotation = self.rotation - int(0x10000 * angle / math.pi / 2) & 0xFFFF

        det = mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0]
        self.scale *= math.sqrt(abs(det))
        if det < 0:
            self.flip_x = not self.flip_x
            self.rotation = -self.rotation & 0xFFFF
