"""
Module providing methods for write Dustforce binary formats including level
files.
"""
import functools
import io
from math import floor, log
from typing import Dict, Iterable, List, Tuple, Union
import zlib

from .bitio import BitIOWriter
from .level import Level
from .exceptions import LevelParseException
from .tile import TileSpriteSet
from .variable import (
    Variable,
    VariableArray,
    VariableBool,
    VariableFloat,
    VariableInt,
    VariableString,
    VariableStruct,
    VariableType,
    VariableUInt,
    VariableVec2,
)


class LevelSegment:
    """Container class with raw information about a segment"""

    def __init__(self):
        self.tiles = [[] for _ in range(256)]
        self.entities = []
        self.props = []
        self.present = True


class LevelRegion:
    """Container class for region data"""

    def __init__(self):
        self.segment_map = {}
        self.backdrop = LevelSegment()
        self.backdrop.present = False

    def get_segment(self, x: int, y: int) -> LevelSegment:
        """Return the segment at the given coordinate within this region"""
        seg_key = ((x // 16) & 0xF, (y // 16) & 0xF)

        seg = self.segment_map.get(seg_key)
        if seg is not None:
            return seg

        seg = LevelSegment()
        self.segment_map[seg_key] = seg
        return seg


class RegionMap:
    """Container class for region/segment information"""

    def __init__(self):
        self.region_map = {}

    def get_region(self, x: int, y: int) -> LevelRegion:
        """Return the region at the given coordinate"""
        reg_ky = (x // 256, y // 256)
        reg = self.region_map.get(reg_ky)
        if reg is not None:
            return reg

        reg = LevelRegion()
        self.region_map[reg_ky] = reg
        return reg

    def get_segment(self, x: int, y: int) -> LevelSegment:
        """Return the segment at the given coordinate"""
        return self.get_region(x, y).get_segment(x, y)

    def get_region_keys(self) -> List[Tuple[int, int]]:
        """Return a list of the region keys sorted in the order required by the
        Dustforce level format."""

        def norm_for_sort(coord):
            """Do some stuff to order regions correctly"""
            x = coord[0]
            y = coord[1]
            if x < 0:
                x += 1 << 16
            if y < 0:
                y += 1 << 16
            return (x, y)

        return sorted(self.region_map, key=norm_for_sort)


def compute_region_map(level: Level) -> RegionMap:
    """Constructs a region map based on the passed level file. This
    structure separates all the tiles/props/entities into their respective
    regions as is used in the underlying binary representation.
    """
    rmap = RegionMap()
    for (layer, tx, ty), tile in level.tiles.items():
        rmap.get_segment(tx, ty).tiles[layer].append((tx & 0xF, ty & 0xF, tile))

    for id_num, (x, y, entity) in level.entities.items():
        rmap.get_segment(int(x / 48), int(y / 48)).entities.append(
            (id_num, x, y, entity)
        )

    for id_num, (layer, x, y, prop) in level.props.items():
        rmap.get_segment(int(x / 48), int(y / 48)).props.append(
            (id_num, layer, x, y, prop)
        )

    if level.backdrop is None:
        return rmap

    for (layer, x, y), tile in level.backdrop.tiles.items():
        seg = rmap.get_region(x * 16, y * 16).backdrop
        seg.present = True
        seg.tiles[layer].append((x & 0xF, y & 0xF, tile))

    for id_num, (layer, x, y, prop) in level.backdrop.props.items():
        seg = rmap.get_region(int(x / 48), int(y / 48)).backdrop
        seg.present = True
        seg.props.append((id_num, layer, x, y, prop))

    return rmap


class DFWriter(BitIOWriter):
    """Helper class to write Dustforce binary files"""

    def write_float(self, ibits: int, fbits: int, val: float) -> None:
        """Write a float to the output stream"""
        ipart = abs(floor(val))
        fpart = int((val - floor(val)) * (2 ** (fbits - 1)))
        self.write(1, 1 if val < 0 else 0)
        self.write(ibits - 1, ipart)
        self.write(fbits, fpart)

    def write_6bit_str(self, text: str) -> None:
        """Write a '6-bit' string to the output stream"""
        self.write(6, len(text))
        for ch in text:
            v = ord(ch)
            if ord("0") <= v <= ord("9"):
                self.write(6, v - ord("0"))
            elif ord("A") <= v <= ord("Z"):
                self.write(6, v - ord("A") + 10)
            elif ord("a") <= v <= ord("z"):
                self.write(6, v - ord("a") + 37)
            elif ch == "_":
                self.write(6, 36)
            else:
                self.write(6, 63)

    def write_var_type(self, var: Variable, allow_continuation=True) -> None:
        """Write a variable to the output stream"""
        value = var.value
        if isinstance(var, VariableBool):
            self.write(1, 1 if value else 0)
            return
        if isinstance(var, (VariableUInt, VariableInt)):
            self.write(32, value)
            return
        if isinstance(var, VariableFloat):
            self.write_float(32, 32, value)
            return

        if isinstance(var, VariableString):
            width = (1 << 16) - 1
            for i in range(0, 1 + len(value) // width):
                if i > 0:
                    if not allow_continuation:
                        break
                    self.write(4, var._vtype)
                    self.write_6bit_str("ctn")
                vs = value[i * width : (i + 1) * width]

                self.write(16, len(vs))
                self.write_bytes(vs)
            return

        if isinstance(var, VariableVec2):
            self.write_float(32, 32, value[0])
            self.write_float(32, 32, value[1])
            return

        if isinstance(var, VariableArray):
            atype = value[0]
            arr = value[1]
            arrlen = len(arr)
            width = (1 << 16) - 1
            if atype == VariableType.STRING:
                for x in arr:
                    arrlen += len(x.value) // width
            self.write(4, atype._vtype)
            self.write(16, arrlen)
            for x in arr:
                if atype == VariableType.STRING:
                    xs = x.value
                    for i in range(0, 1 + len(xs) // width):
                        self.write_var_type(
                            VariableString(xs[i * width : (i + 1) * width]), False
                        )
                else:
                    self.write_var_type(x)
            return

        if isinstance(var, VariableStruct):
            self.write_var_map(value)
            return

        raise LevelParseException("unknown var type")

    def write_var(self, key: str, var: Variable) -> None:
        """Write a named variable to the output stream"""
        self.write(4, var._vtype)
        self.write_6bit_str(key)
        self.write_var_type(var)

    def write_var_map(self, variables: Dict[str, Variable]) -> None:
        """Write a variable map to the output stream"""
        for key, var in variables.items():
            self.write_var(key, var)
        self.write(4, VariableType.NULL)

    def write_segment(self, seg_x: int, seg_y: int, segment: LevelSegment) -> None:
        """Write a segment to the output stream"""
        assert self.aligned()

        start_index = self.bit_tell()
        self.bit_seek(start_index + 200)

        flags = 0
        tiles = [(i, segment.tiles[i]) for i in range(21) if segment.tiles[i]]

        (dust_filth, enemy_filth, tile_surface, dustblock_filth) = (0, 0, 0, 0)

        dusts = []
        if tiles:
            flags |= 1

            self.write(8, len(tiles))
            for layer, tilelayer in tiles:
                self.write(8, layer)
                self.write(10, len(tilelayer))

                for x, y, tile in sorted(tilelayer, key=lambda x: (x[1], x[0])):
                    if layer == 19 and tile.has_filth():
                        dusts.append((x, y, tile))
                    if layer == 19:
                        if tile.is_dustblock():
                            dustblock_filth += 1
                        for edge in tile.edge_data:
                            if edge.filth_spike:
                                continue

                            if edge.filth_sprite_set != TileSpriteSet.NONE_0:
                                dust_filth += 1

                            if edge.solid and edge.visible:
                                tile_surface += 1

                    self.write(5, x)
                    self.write(5, y)
                    self.write(5, tile.shape)
                    self.write(3, tile.tile_flags)
                    self.write_bytes(tile._pack_tile_data())

        if dusts:
            flags |= 2

            self.write(10, len(dusts))
            for (x, y, tile) in dusts:
                self.write(5, x)
                self.write(5, y)
                self.write_bytes(tile._pack_dust_data())

        if segment.props:
            flags |= 8

            self.write(16, len(segment.props))
            for id_num, layer, x, y, prop in segment.props:
                self.write(32, id_num)
                self.write(8, layer)
                self.write(8, prop.layer_sub)

                scale_lg = int(round(log(prop.scale) / log(50.0) * 24.0)) + 32
                x_scale = (scale_lg // 7) ^ 0x4
                y_scale = (scale_lg % 7) ^ 0x4
                x_int = int(abs(x))
                y_int = int(abs(y))
                x_sgn = 1 if x < 0 else 0
                y_sgn = 1 if y < 0 else 0
                self.write(1, x_sgn)
                self.write(27, x_int)
                self.write(4, x_scale)
                self.write(1, y_sgn)
                self.write(27, y_int)
                self.write(4, y_scale)

                self.write(16, prop.rotation)
                self.write(1, 1 if prop.flip_x else 0)
                self.write(1, 1 if prop.flip_y else 0)
                self.write(8, prop.prop_set)
                self.write(12, prop.prop_group)
                self.write(12, prop.prop_index)
                self.write(8, prop.palette)

        if segment.entities:
            flags |= 4

            extra_names_io = io.BytesIO()
            extra_names_writer = DFWriter(extra_names_io)
            self.write(16, len(segment.entities))
            for (id_num, x, y, entity) in segment.entities:
                enemy_filth += getattr(entity, "FILTH", 0)
                self.write(32, id_num)
                if entity.etype.startswith("z_") or entity.etype == "entity":
                    self.write_6bit_str("entity")
                    extra_names_writer.write_6bit_str(entity.etype)
                else:
                    self.write_6bit_str(entity.etype)
                self.write_float(32, 8, x)
                self.write_float(32, 8, y)
                self.write(16, entity.rotation)
                self.write(8, entity.layer)
                self.write(1, 0 if entity.flipX else 1)
                self.write(1, 0 if entity.flipY else 1)
                self.write(1, 1 if entity.visible else 0)
                self.write_var_map(entity.variables)

            extra_names_writer.align()
            entity_names_pos = self.bit_tell()
            self.write_bytes(extra_names_io.getvalue())
            self.align()
            self.write(32, self.bit_tell() - entity_names_pos)

        self.align()

        end_index = self.bit_tell()
        self.bit_seek(start_index)

        self.write(32, (end_index - start_index) // 8)
        self.write(16, 8)
        self.write(8, seg_x)
        self.write(8, seg_y)
        self.write(8, 16)

        self.write(32, 0)
        self.write(16, dust_filth)
        self.write(16, enemy_filth)

        self.write(16, tile_surface)
        self.write(16, dustblock_filth)

        self.write(32, flags)
        self.bit_seek(end_index)

    def write_region(self, x: int, y: int, region: LevelRegion) -> None:
        """Writes a level region to the output stream"""
        segments_io = io.BytesIO()
        with DFWriter(segments_io) as segments_writer:
            for coord, segment in sorted(region.segment_map.items()):
                segments_writer.write_segment(coord[0], coord[1], segment)
            if region.backdrop.present:
                segments_writer.write_segment(0, 0, region.backdrop)
            uncompressed_data = segments_io.getvalue()

        compressed_data = zlib.compress(uncompressed_data)

        self.write(32, 17 + len(compressed_data))
        self.write(32, len(uncompressed_data))
        self.write(16, x)
        self.write(16, y)
        self.write(16, 14)
        self.write(16, len(region.segment_map))
        self.write(8, 1 if region.backdrop.present else 0)
        self.write_bytes(compressed_data)

    # Should match the number of bits written by write_metadata
    METADATA_BIT_SIZE = 224

    def write_metadata(self, level: Level) -> None:
        """Write a level metadata block to the output stream."""
        self.write_bytes(b"DF_MTD")
        self.write(16, 4)
        self.write(32, 0)
        self.write(32, level.calculate_max_id(reset=False) + 1)
        self.write(32, 0)
        self.write(32, 0)
        self.write(32, 0)

    def write_var_file(self, header: bytes, var_data: Dict[str, Variable]) -> None:
        """Write a var file to the output stream"""
        assert self.aligned()

        start_index = self.bit_tell()
        self.bit_seek(start_index + 8 * len(header) + 48)

        self.write_var_map(var_data)
        self.align()
        end_index = self.bit_tell()

        self.bit_seek(start_index)

        self.write_bytes(header)
        self.write(16, 1)
        self.write(32, (end_index - start_index) // 8)
        self.bit_seek(end_index)

    def write_level_ex(
        self,
        level: Level,
        region_offsets: List[int],
        region_data: Union[bytes, Iterable[bytes]],
    ) -> None:
        """
        Writes `level` to the output stream. This is the advanced API for
        efficiently modifiying level metadata. If region_offsets is non-empty
        this will use `region_offsets` and `region_data` to populate the region
        data section of the output rather than calculating it from `level`. See
        :meth:`write_level` for the standard API.

        Arguments:
            level (Level): The level file to write
            region_offsets (list[int]): Region offset metadata as returned by
                :meth:`DFReader.read_level_ex`. If empty this behaves the same
                as :meth:`write_level`.
            region_data: (bytes | Iterable[bytes]): Bytes data (or an iterable
                of bytes data) to write in the region section of the map. If
                `region_offsets` is empty this argument is ignored.
        """
        assert self.aligned()

        start_index = self.bit_tell()
        header_size = 160 + self.METADATA_BIT_SIZE + len(level.sshot) * 8

        self.bit_seek(start_index + header_size)

        # Write variable mapping and record size
        self.write_var_map(level.variables)

        # Skip over the region directory for now
        if region_offsets:
            num_regions, end_index = self._write_regions_raw(
                region_offsets, region_data
            )
        else:
            num_regions, end_index = self._write_regions_from_level(level)

        # Got back to start and rewrite header.
        self.bit_seek(start_index)
        self.write_bytes(b"DF_LVL")
        self.write(16, 44)
        self.write(32, (end_index - start_index) // 8)
        self.write(32, num_regions)
        self.write_metadata(level)
        self.write(32, len(level.sshot))
        self.write_bytes(level.sshot)
        self.bit_seek(end_index)

    def _write_regions_raw(
        self, region_offsets: List[int], region_data: Union[bytes, Iterable[bytes]]
    ) -> Tuple[int, int]:
        """Helper function to write region data from raw offset/data
        information.

        Returns:
            The ending bit index.
        """
        for region_offset in region_offsets[:-1]:
            self.write(32, region_offset)

        self.align()

        start_index = self.bit_tell()
        if isinstance(region_data, bytes):
            self.write_bytes(region_data)
        else:
            for data in region_data:
                self.write_bytes(data)
        end_index = self.bit_tell()

        if end_index - start_index != region_offsets[-1] * 8:
            raise LevelParseException("got unexpected amount of regiond ata")

        return len(region_offsets) - 1, self.bit_tell()

    def _write_regions_from_level(self, level: Level) -> Tuple[int, int]:
        """Helper function to write region data from the level

        Returns:
            The ending bit index.
        """
        rmap = compute_region_map(level)
        region_dir_index = self.bit_tell()
        region_data_index = (region_dir_index + 32 * len(rmap.region_map) + 7) & ~0x7
        self.bit_seek(region_data_index)
        region_offsets = []

        # Write the region data
        for rx, ry in rmap.get_region_keys():
            self.align()
            region_offsets.append((self.bit_tell() - region_data_index) // 8)
            self.write_region(rx, ry, rmap.region_map[(rx, ry)])

        end_index = self.bit_tell()

        # Go back and write the region directory. This might not be
        # byte aligned which doesn't can zero previous bits in the partial byte.
        # Since the first element is zero anyway we just skip it to avoid
        # writing over the var map.
        self.bit_seek(region_dir_index + 32, allow_unaligned=True)
        for region_offset in region_offsets[1:]:
            self.write(32, region_offset)

        return len(rmap.region_map), end_index

    def write_level(self, level: Level) -> None:
        """Writes `level` to the output stream.

        Arguments:
            level (Level): The level file to write
        """
        self.write_level_ex(level, [], b"")

    write_stat_file = functools.partial(write_var_file, header=b"DF_STA")
    write_config_file = functools.partial(write_var_file, header=b"DF_CFG")
    write_fog_file = functools.partial(write_var_file, header=b"DF_FOG")


def write_level(level: Level) -> bytes:
    """Convenience method to write a map file and return the written bytes."""
    with DFWriter(io.BytesIO()) as writer:
        writer.write_level(level)
        return writer.data.getvalue()


# pylint: disable=fixme
# TODO, support DF_EMT, DF_PRT, DF_WND