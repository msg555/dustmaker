from .Map import Map
from .Tile import Tile, TileShape
from .Prop import Prop
from .Entity import Entity
from .Var import Var, VarType
from .BitReader import BitReader
from .MapException import MapParseException
from .LevelType import LevelType

import zlib

from math import pow

def read_expect(reader, data):
  for x in data:
    if x != reader.read(8):
      raise MapParseException("unexpected data")

def read_float(reader, ibits, fbits):
  sign = 1 - 2 * reader.read(1)
  ipart = reader.read(ibits - 1)
  fpart = reader.read(fbits)
  return sign * ipart + 1.0 * fpart / (1 << (fbits - 1))

def read_6bit_str(reader):
  len = reader.read(6)
  chrs = []
  for i in range(len):
    v = reader.read(6)
    if v < 10:
      chrs.append(chr(ord('0') + v))
    elif v < 36:
      chrs.append(chr(ord('A') + v - 10))
    elif v == 36:
      chrs.append('_')
    elif v < 63:
      chrs.append(chr(ord('a') + v - 37))
    else:
      chrs.append('{')
  return ''.join(chrs)

def read_var_type(reader, type, allow_continuation = True):
  if type == VarType.NULL: return None
  if type == VarType.BOOL: return reader.read(1) == 1
  if type == VarType.UINT: return reader.read(32)
  if type == VarType.INT: return reader.read(32, True)
  if type == VarType.FLOAT: return read_float(reader, 32, 32)

  if type == VarType.STRING:
    chrs = []
    continuation = True
    while continuation:
      slen = reader.read(16)
      for i in range(slen):
        chrs.append(chr(reader.read(8)))

      continuation = False
      if allow_continuation and slen == (1 << 16) - 1:
        # Skip past header data that's there to allow legacy clients to parse
        # somewhat successfully.
        continuation = True
        reader.read(4)
        read_6bit_str(reader)

    return ''.join(chrs)

  if type == VarType.VEC2:
    f0 = read_float(reader, 32, 32)
    f1 = read_float(reader, 32, 32)
    return (f0, f1)

  if type == VarType.ARRAY:
    atype = VarType(reader.read(4))
    alen = reader.read(16)
    val = []
    continuation = False
    for i in range(alen):
      elem = read_var_type(reader, atype, False)
      if continuation:
        val[-1].value += elem
      else:
        val.append(Var(atype, elem))
      continuation = atype == VarType.STRING and len(elem) == (1 << 16) - 1

    return (atype, val)

  if type == VarType.STRUCT:
    return read_var_map(reader)

  raise MapParseException("unknown var type")

def read_var(reader):
  type = VarType(reader.read(4))
  if type == VarType.NULL:
    return None

  str = read_6bit_str(reader)
  return (str, Var(type, read_var_type(reader, type)))

def read_var_map(reader):
  result = {}
  while True:
    var = read_var(reader)
    if var is None:
      return result
    result[var[0]] = var[1]

def read_segment(reader, map, xoffset, yoffset, config):
  start_index = reader.get_index()

  segment_size = reader.read(32)
  version = reader.read(16)
  xoffset += reader.read(8) * 16
  yoffset += reader.read(8) * 16
  segmentWidth = reader.read(8)

  if version > 4:
    level_uid = reader.read(32)
    dust_filth = reader.read(16)
    enemy_filth = reader.read(16)
  if version > 5:
    tile_surface = reader.read(16)
    dustblock_filth = reader.read(16)

  flags = reader.read(32)
  if flags & 1:
    layers = reader.read(8)
    for i in range(layers):
      layer = reader.read(8)
      tiles = reader.read(10)

      for j in range(tiles):
        xpos = reader.read(5)
        ypos = reader.read(5)
        shape = reader.read(8)
        data = reader.read_bytes(12)
        if shape & 0x80:
          map.add_tile(layer, xoffset + xpos, yoffset + ypos,
                       Tile(TileShape(shape & 0x1F), data))

  if flags & 2:
    dusts = reader.read(10)
    for i in range(dusts):
      xpos = reader.read(5)
      ypos = reader.read(5)
      data = reader.read_bytes(12)
      tile = map.get_tile(19, xoffset + xpos, yoffset + ypos)
      if tile != None:
        tile.dust_data = bytearray(data)

  if flags & 8:
    props = reader.read(16)
    for i in range(props):
      id = reader.read(32, True)
      if id < 0:
        continue

      layer = reader.read(8)
      layer_sub = reader.read(8)

      scale = 1
      if version > 6 or config['scaled_props']:
        x_sgn = reader.read(1)
        x_int = reader.read(27)
        x_scale = (reader.read(4) & 0x7) ^ 0x4
        y_sgn = reader.read(1)
        y_int = reader.read(27)
        y_scale = (reader.read(4) & 0x7) ^ 0x4

        xpos = (-1 if x_sgn != 0 else 1) * x_int
        ypos = (-1 if y_sgn != 0 else 1) * y_int

        scale_lg = x_scale * 7 + y_scale
        scale = pow(50.0, (scale_lg - 32.0) / 24.0)
      else:
        xpos = read_float(reader, 28, 4)
        ypos = read_float(reader, 28, 4)

      rotation = reader.read(16)
      flip_x = reader.read(1) != 0
      flip_y = reader.read(1) != 0
      prop_set = reader.read(8)
      prop_group = reader.read(12)
      prop_index = reader.read(12)
      palette = reader.read(8)

      map.add_prop(layer, xpos / 48, ypos / 48, Prop(
                   layer_sub, rotation, flip_x, flip_y, scale,
                   prop_set, prop_group, prop_index, palette), id)

  if flags & 4:
    extra_names_reader = BitReader(b"")
    if version > 7:
      extra_names_reader = BitReader(reader.data)
      extra_names_reader.set_index(start_index + (segment_size - 4) * 8)
      extra_names_index = extra_names_reader.read(32)
      extra_names_reader.skip(-extra_names_index - 32)

    entities = reader.read(16)
    for i in range(entities):
      id = reader.read(32, True)
      if id < 0:
        continue

      type = read_6bit_str(reader)
      if type == "entity":
        type = read_6bit_str(extra_names_reader)

      xpos = read_float(reader, 32, 8)
      ypos = read_float(reader, 32, 8)
      rotation = reader.read(16)
      layer = reader.read(8)
      faceX = reader.read(1)
      faceY = reader.read(1)
      visible = reader.read(1)
      vars = read_var_map(reader)

      map.add_entity(xpos / 48, ypos / 48, Entity._from_raw(
                     type, vars, rotation, layer,
                     faceX == 0, faceY == 0, visible == 1), id)

  reader.set_index(start_index + segment_size * 8)

def read_region(reader, map, config):
  region_len = reader.read(32)
  uncompressed_len = reader.read(32)
  offx = reader.read(16, True)
  offy = reader.read(16, True)
  version = reader.read(16)
  segments = reader.read(16)
  has_backdrop = reader.read(8) != 0

  reader = BitReader(zlib.decompress(reader.read_bytes(region_len - 17)))
  for i in range(segments):
    reader.align(8)
    read_segment(reader, map, offx * 256, offy * 256, config)

  if has_backdrop:
    reader.align(8)
    read_segment(reader, map.backdrop, offx * 16, offy * 16, config)

def read_metadata(reader):
  read_expect(reader, b"DF_MTD")

  version = reader.read(16)
  region_offset = reader.read(32)
  entityUid = reader.read(32)
  propUid = reader.read(32)
  deprecatedSaveUid = reader.read(32)
  regionUidDeprecated = reader.read(32)
  return {
    'version': version,
    'entityUid': entityUid,
    'propUid': propUid,
    'deprecatedSaveUid': deprecatedSaveUid,
    'regionUidDeprecated': regionUidDeprecated,
  }

def read_map(data):
  """ Returns a Map object parsed from `data` in the Dustforce level format.

      data - A sequence of bytes representing a Dustforce level.

      On error raises a MapParseException.
  """
  try:
    reader = BitReader(data)
    read_expect(reader, b"DF_LVL")

    version = reader.read(16)
    if version <= 42:
      raise MapParseException("unsupported level version")

    filesize = reader.read(32)
    num_regions = reader.read(32)
    meta = read_metadata(reader)

    sshot_data = b""
    if version > 43:
      sshot_len = reader.read(32)
      sshot_data = reader.read_bytes(sshot_len)

    map = Map()
    map.vars = read_var_map(reader)
    map.sshot = sshot_data

    config = {"scaled_props": map.level_type() == LevelType.DUSTMOD}

    reader.align(8)
    reader.skip(num_regions * 32)
    for i in range(num_regions):
      read_region(reader, map, config)
    return map
  except MapParseException as e:
    raise e
  except Exception as e:
    raise MapParseException(e)

def read_var_file(header, data):
  try:
    reader = BitReader(data)
    read_expect(reader, header)
    version = reader.read(16)
    statSize = reader.read(32)
    return read_var_map(reader)
  except MapParseException as e:
    raise e
  except Exception as e:
    raise MapParseException(e)

def read_stat_file(data):
  return read_var_file(b"DF_STA", data)

def read_config_file(data):
  return read_var_file(b"DF_CFG", data)

def read_fog_file(data):
  return read_var_file(b"DF_FOG", data)

# TODO, support DF_EMT, DF_PRT, DF_WND
