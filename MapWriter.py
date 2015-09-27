from Map import Map
from Tile import Tile
from Prop import Prop
from Entity import Entity
from Var import Var, VarType
from BitWriter import BitWriter
from MapException import MapParseException

import zlib
from math import floor

def write_float(writer, ibits, fbits, val):
  ipart = abs(floor(val))
  fpart = int((val - floor(val)) * (2 ** (fbits - 1)))
  writer.write(1, 1 if val < 0  else 0)
  writer.write(ibits - 1, ipart)
  writer.write(fbits, fpart)

def write_6bit_str(writer, str):
  writer.write(6, len(str))
  for ch in str:
    v = ord(ch)
    if ord('0') <= v and v <= ord('9'):
      writer.write(6, v - ord('0'))
    elif ord('A') <= v and v <= ord('Z'):
      writer.write(6, v - ord('A') + 10)
    elif ord('a') <= v and v <= ord('z'):
      writer.write(6, v - ord('a') + 37)
    elif ch == '_':
      writer.write(6, 36)
    else:
      writer.write(6, 63)

def write_var_type(writer, var):
  type = var.type
  value = var.value
  if type == VarType.NULL: return
  if type == VarType.BOOL: return writer.write(1, 1 if value else 0)
  if type == VarType.UINT: return writer.write(32, value)
  if type == VarType.INT: return writer.write(32, value)
  if type == VarType.FLOAT: return write_float(writer, 32, 32, value)

  if type == VarType.STRING:
    writer.write(16, len(value))
    for ch in value:
      writer.write(8, ord(ch))
    return

  if type == VarType.VEC2:
    write_float(writer, 32, 32, value[0])
    write_float(writer, 32, 32, value[1])
    return

  if type == VarType.ARRAY:
    atype = value[0]
    arr = value[1]
    writer.write(4, atype)
    writer.write(16, len(arr))
    for x in arr:
      write_var_type(writer, x)
    return

  raise MapParseException("unknown var type")

def write_var(writer, key, var):
  writer.write(4, var.type)
  write_6bit_str(writer, key)
  write_var_type(writer, var)

def write_var_map(writer, vars):
  for key in vars:
    write_var(writer, key, vars[key])
  writer.write(4, VarType.NULL)

def write_segment(base_writer, seg_x, seg_y, segment):
  writer = BitWriter()

  flags = 0
  tiles = {i: segment['tiles'][i] for i in range(21) if segment['tiles'][i]}

  dusts = []
  if tiles:
    flags |= 1

    writer.write(8, len(tiles))
    for (layer, tilelayer) in tiles.items():
      writer.write(8, layer)
      writer.write(10, len(tilelayer))

      ordered_tiles = []
      for (coord, tile) in tilelayer.items():
        ordered_tiles.append((coord[1], coord[0], tile))
      ordered_tiles.sort()

      for (y, x, tile) in ordered_tiles:
        if layer == 19 and tile.dust_data != None:
          dusts.append((y, x, tile))
        writer.write(5, x)
        writer.write(5, y)
        writer.write(8, tile.shape)

        if len(tile.tile_data) != 12:
          raise MapParseException("invalid tile data")
        writer.write_bytes(tile.tile_data)

  if dusts:
    flags |= 2

    writer.write(10, len(dusts))
    for (y, x, tile) in dusts:
      writer.write(5, x)
      writer.write(5, y)

      if len(tile.dust_data) != 12:
        raise MapParseException("invalid dust data")
      writer.write_bytes(tile.dust_data)

  if segment['props']:
    flags |= 8

    writer.write(16, len(segment['props']))
    for (id, layer, x, y, prop) in segment['props']:
      writer.write(32, id)
      writer.write(8, layer)
      writer.write(8, prop.layer_sub)
      write_float(writer, 28, 4, x)
      write_float(writer, 28, 4, y)
      writer.write(16, prop.rotation)
      writer.write(1, 1 if prop.scale_x else 0)
      writer.write(1, 1 if prop.scale_y else 0)
      writer.write(8, prop.prop_set)
      writer.write(12, prop.prop_group)
      writer.write(12, prop.prop_index)
      writer.write(8, prop.palette)

  if segment['entities']:
    flags |= 4

    writer.write(16, len(segment['entities']))
    for (id, x, y, entity) in segment['entities']:
      writer.write(32, id)
      write_6bit_str(writer, entity.type)
      write_float(writer, 32, 8, x)
      write_float(writer, 32, 8, y)
      writer.write(16, entity.rotation)
      writer.write(8, entity.unk1)
      writer.write(1, entity.unk2)
      writer.write(1, entity.unk3)
      writer.write(1, entity.unk4)
      write_var_map(writer, entity.vars)

  writer_body = writer
  writer = base_writer

  writer.write(32, 25 + writer_body.byte_count())
  writer.write(16, 6)
  writer.write(8, seg_x)
  writer.write(8, seg_y)
  writer.write(8, 16)

  writer.write(32, 0)
  writer.write(16, 0)
  writer.write(16, 0)

  writer.write(16, 25)
  writer.write(16, 0)

  writer.write(32, flags)
  writer.write_bytes(writer_body.bytes())

def write_region(x, y, region):
  writer = BitWriter()
  for coord in region['segments']:
    writer.align(8)
    write_segment(writer, coord[0], coord[1], region['segments'][coord])
  if region['backdrop']['present']:
    writer.align(8)
    write_segment(writer, 0, 0, region['backdrop'])

  data = zlib.compress(writer.bytes())

  writer_header = BitWriter()
  writer_header.write(32, writer.byte_count())
  writer_header.write(16, x)
  writer_header.write(16, y)
  writer_header.write(16, 0)
  writer_header.write(16, len(region['segments']))
  writer_header.write(8, 1 if region['backdrop']['present'] else 0)

  return b"".join([writer_header.bytes(), data])

def segment_get(segment_map, x, y):
  sx = int(floor(x / 16)) & 0xF
  sy = int(floor(y / 16)) & 0xF
  if (sx, sy) in segment_map:
    return segment_map[(sx, sy)]

  seg = dict(
    tiles = [{} for x in range(21)],
    entities = [],
    props = [],
  )
  segment_map[(sx, sy)] = seg
  return seg

def region_get(region_map, x, y):
  rx = int(floor(x / 256))
  ry = int(floor(y / 256))
  if (rx, ry) in region_map:
    return region_map[(rx, ry)]

  reg = dict(
    segments = {},
    backdrop = dict(
      present = False,
      tiles = [{} for x in range(21)],
      entities = [],
      props = [],
    )
  )
  region_map[(rx, ry)] = reg
  return reg

def compute_region_map(map):
  region_map = {}
  tiles = map.tile_map()
  for coord in tiles:
    layer = coord[0]
    x = coord[1]
    y = coord[2]
    seg = segment_get(region_get(region_map, x, y)['segments'], x, y)
    seg['tiles'][layer][(x & 0xF, y & 0xF)] = tiles[coord]

  for id in map.entity_ids:
    x = map.get_entity_xposition(id)
    y = map.get_entity_xposition(id)
    seg = segment_get(region_get(region_map, x, y)['segments'], x, y)
    seg['entities'].append((id, x, y, map.get_entity(id)))

  for id in map.prop_ids:
    x = map.get_prop_xposition(id)
    y = map.get_prop_yposition(id)
    layer = map.get_prop_layer(id)
    seg = segment_get(region_get(region_map, x, y)['segments'], x, y)
    seg['props'].append((id, layer, x, y, map.get_prop(id)))
    
  if map.backdrop:
    tiles = map.backdrop.tile_map()
    for coord in tiles:
      layer = coord[0]
      x = coord[1]
      y = coord[2]
      seg = segment_get(region_get(region_map, x * 16, y * 16)['backdrop'],
                                   0, 0)
      seg['present'] = True
      seg['tiles'][layer][(x & 0xF, y & 0xF)] = tiles[coord]

    for id in map.backdrop.prop_ids:
      x = map.backdrop.get_prop_xposition(id)
      y = map.backdrop.get_prop_yposition(id)
      layer = map.backdrop.get_prop_layer(id)
      seg = segment_get(region_get(region_map, x * 16, y * 16)['backdrop'],
                                   0, 0)
      seg['present'] = True
      seg['props'].append((id, layer, x, y, map.backdrop.get_prop(id)))
  return region_map

def write_metadata(writer, var_size, map):
  writer.write_bytes(b"DF_MTD")
  writer.write(16, 4)
  writer.write(32, var_size + 32 + len(map.sshot))
  writer.write(32, 0)
  writer.write(32, 0)
  writer.write(32, 0)
  writer.write(32, 0)

def write_map(map):
  writer_front = BitWriter()
  write_var_map(writer_front, map.vars)
  writer_front.align(8)
  var_size = writer_front.byte_count()

  writer_back = BitWriter()
  region_map = compute_region_map(map)
  for coord in region_map:
    writer_back.align(8)
    writer_front.write(32, writer_back.pos >> 3)
    reg_data = write_region(coord[0], coord[1], region_map[coord])
    writer_back.write(32, len(reg_data) + 4)
    writer_back.write_bytes(reg_data)
    
  writer_header = BitWriter()
  writer_header.write(32, len(region_map))
  write_metadata(writer_header, var_size, map)
  writer_header.write(32, len(map.sshot))
  writer_header.write_bytes(map.sshot)

  writer = BitWriter()
  writer.write_bytes(b"DF_LVL")
  writer.write(16, 44)
  writer.write(32, 12 + len(writer_header.bytes()) +
                        len(writer_front.bytes()) +
                        len(writer_back.bytes()))
  writer.write_bytes(writer_header.bytes())
  writer.write_bytes(writer_front.bytes())
  writer.write_bytes(writer_back.bytes())
  return writer.bytes()
