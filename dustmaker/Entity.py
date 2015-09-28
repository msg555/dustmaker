class Entity:
  def __init__(self, type, rotation, unk1, unk2, unk3, unk4, vars):
    self.type = type
    self.rotation = rotation
    self.unk1 = unk1
    self.unk2 = unk2
    self.unk3 = unk3
    self.unk4 = unk4
    self.vars = vars

  def __repr__(self):
    return "Entity: (%s, %d, %d, %d, %d, %d, %s)" % (
              self.type, self.rotation, self.unk1, self.unk2, self.unk3,
              self.unk4, repr(self.vars))
