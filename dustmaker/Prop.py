import math


class Prop:

    def __init__(self, layer_sub, rotation, scale_x, scale_y,
                 prop_set, prop_group, prop_index, palette):
        self.layer_sub = layer_sub
        self.rotation = rotation
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.prop_set = prop_set
        self.prop_group = prop_group
        self.prop_index = prop_index
        self.palette = palette

    def transform(self, mat):
        angle = math.atan2(mat[1][1], mat[1][0]) - math.pi / 2
        self.rotation = self.rotation - \
            int(0x10000 * angle / math.pi / 2) & 0xFFFF

        if mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0] < 0:
            self.scale_x = not self.scale_x
            self.rotation = -self.rotation & 0xFFFF
