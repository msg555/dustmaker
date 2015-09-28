from enum import IntEnum

class VarType(IntEnum):
  NULL = 0
  BOOL = 1
  UINT = 2
  INT = 3
  FLOAT = 4
  STRING = 5
  VEC2 = 10
  ARRAY = 15

class Var:
  def __init__(self, type, value):
    self.type = type
    self.value = value

  def __repr__(self):
    return "Var (%s, %s)" % (repr(self.type), repr(self.value))
