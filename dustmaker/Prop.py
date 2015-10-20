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

  def flip_horizontal(self):
    self.scale_x = not self.scale_x
    self.rotation = -self.rotation & 0xFFFF

  def flip_vertical(self):
    self.rotation = self.rotation + (1 << 15) & 0xFFFF
    self.flip_horizontal()
