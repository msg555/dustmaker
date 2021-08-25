"""
Module providing methods for write Dustforce binary formats including level
files.
"""
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


class _LevelSegment:
    """Container class with raw information about a segment"""

    def __init__(self):
        self.tiles = [[] for _ in range(256)]
        self.entities = []
        self.props = []
        self.present = True


class _LevelRegion:
    """Container class for region data"""

    def __init__(self):
        self.segment_map = {}
        self.backdrop = _LevelSegment()
        self.backdrop.present = False

    def get_segment(self, x: int, y: int) -> _LevelSegment:
        """Return the segment at the given coordinate within this region"""
        seg_key = ((x // 16) & 0xF, (y // 16) & 0xF)

        seg = self.segment_map.get(seg_key)
        if seg is not None:
            return seg

        seg = _LevelSegment()
        self.segment_map[seg_key] = seg
        return seg


class _RegionMap:
    """Container class for region/segment information."""

    def __init__(self):
        self.region_map = {}

    def get_region(self, x: int, y: int) -> _LevelRegion:
        """Return the region at the given coordinate"""
        reg_ky = (x // 256, y // 256)
        reg = self.region_map.get(reg_ky)
        if reg is not None:
            return reg

        reg = _LevelRegion()
        self.region_map[reg_ky] = reg
        return reg

    def get_segment(self, x: int, y: int) -> _LevelSegment:
        """Return the segment at the given coordinate"""
        return self.get_region(x, y).get_segment(x, y)

    def get_region_keys(self) -> List[Tuple[int, int]]:
        """Return a list of the region keys sorted in the order required by the
        Dustforce level format.
        """

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


def _compute_region_map(level: Level) -> _RegionMap:
    """Constructs a region map based on the passed level file. This
    structure separates all the tiles/props/entities into their respective
    regions as is used in the underlying binary representation.
    """
    rmap = _RegionMap()
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
        """Write a float `val` to the output stream

        Arguments:
            ibits (int): Number of integer bits
            fbits (int): Number of fractional bits
            val (float): The floating point number to write
        """
        ipart = abs(floor(val))
        fpart = int((val - floor(val)) * (2 ** (fbits - 1)))
        self.write(1, 1 if val < 0 else 0)
        self.write(ibits - 1, ipart)
        self.write(fbits, fpart)

    def write_6bit_str(self, text: str) -> None:
        """Write a '6-bit' string. These are strings with length between
        0 and 63 inclusive that contain only alpha-numeric lower and uppercase
        characters in addition to '_' and '{'.

        Raises:
            ValueError: If length of string exceeds 63
            ValueError: If invalid character is present
        """
        if len(text) > 63:
            raise ValueError("6-bit str too long")

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
            elif ch == "{":
                self.write(6, 63)
            else:
                raise ValueError("invalid character in 6-bit string")

    def write_variable(self, var: Variable) -> None:
        """Write a variable to the output stream. This does not write the
        type of the variable, that will need to be encoded somewhere else if
        needed.

        Arguments:
            var (Variable): The variable to write to the stream.

        Raises:
            ValueError: If a VariableString value is longer than 65535 bytes.
                Note that structs and arrays each handle their string sub-elements
                in a way that they may be longer than this limit.
            ValueError: If a VariableArray has more than 65535 elements including
                any continuations if the element type is VariableString.
            LevelParseException: If `var` is of unknown variable type.
        """
        max_width = (1 << 16) - 1

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
            if len(var.value) > max_width:
                raise ValueError("VariableString length too long")

            self.write(16, len(var.value))
            self.write_bytes(var.value)
            return

        if isinstance(var, VariableVec2):
            self.write_float(32, 32, value[0])
            self.write_float(32, 32, value[1])
            return

        if isinstance(var, VariableArray):
            atype, arr = value
            arrlen = len(arr)
            if atype is VariableString:
                for x in arr:
                    arrlen += len(x.value) // max_width
            if arrlen > max_width:
                raise ValueError("VariableArray length too long")

            self.write(4, atype._vtype)
            self.write(16, arrlen)
            if atype is not VariableString:
                for x in arr:
                    self.write_variable(x)
            else:
                for x in arr:
                    # Write array continuations
                    xs = x.value
                    for i in range(0, 1 + len(xs) // max_width):
                        self.write_variable(
                            VariableString(xs[i * max_width : (i + 1) * max_width])
                        )
            return

        if isinstance(var, VariableStruct):
            for elem_key, elem_var in var.value.items():
                if not isinstance(elem_var, VariableString):
                    self.write(4, elem_var._vtype)
                    self.write_6bit_str(elem_key)
                    self.write_variable(elem_var)
                    continue

                # Write struct string continuations
                xs = elem_var.value
                for i in range(0, 1 + len(xs) // max_width):
                    self.write(4, elem_var._vtype)
                    self.write_6bit_str(elem_key)
                    self.write_variable(
                        VariableString(xs[i * max_width : (i + 1) * max_width])
                    )

            self.write(4, VariableType.NULL)

            return

        raise LevelParseException("unknown var type")

    def _write_segment(self, seg_x: int, seg_y: int, segment: _LevelSegment) -> None:
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
                self.write(1, 0 if entity.flip_x else 1)
                self.write(1, 0 if entity.flip_y else 1)
                self.write(1, 1 if entity.visible else 0)
                self.write_variable(VariableStruct(entity.variables))

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

    def _write_region(self, x: int, y: int, region: _LevelRegion) -> None:
        """Writes a level region to the output stream"""
        segments_io = io.BytesIO()
        with DFWriter(segments_io) as segments_writer:
            for coord, segment in sorted(region.segment_map.items()):
                segments_writer._write_segment(coord[0], coord[1], segment)
            if region.backdrop.present:
                segments_writer._write_segment(0, 0, region.backdrop)
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
    _METADATA_BIT_SIZE = 224

    def _write_metadata(self, level: Level) -> None:
        """Write a level metadata block to the output stream."""
        self.write_bytes(b"DF_MTD")
        self.write(16, 4)
        self.write(32, 0)
        self.write(32, level.calculate_max_id(reset=False) + 1)
        self.write(32, 0)
        self.write(32, 0)
        self.write(32, 0)

    def write_var_file(self, header: bytes, var_data: Dict[str, Variable]) -> None:
        """Writes a variable mapping with a given header. There are several
        file types that Dustforce use that are expressed this way including
        notably "stats1" (header=b"DF_STA") and "config" (header=b"DF_CFG").

        Arguments:
            header (bytes): The file header at the start of the stream.
        """
        assert self.aligned()

        start_index = self.bit_tell()
        self.bit_seek(start_index + 8 * len(header) + 48)

        self.write_variable(VariableStruct(var_data))
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
        """Extended version of :meth:`write_level`.

        Writes `level` to the output stream. This is the advanced API for
        efficiently modifiying level metadata. If `region_offsets` is non-empty
        this will use `region_offsets` and `region_data` to populate the region
        data section of the output rather than calculating it from `level`.

        See :meth:`dustmaker.dfreader.DFReader.read_level_ex` for examples
        on how to use this in practice.

        Arguments:
            level (Level): The level file to write
            region_offsets (list[int]): Region offset metadata as returned by
                :meth:`DFReader.read_level_ex`. If empty this behaves the same
                as :meth:`write_level`. If you wish to omit all region data pass
                `[0]` instead.
            region_data: (bytes | Iterable[bytes]): Bytes data (or an iterable
                of bytes data) to write in the region section of the map. If
                `region_offsets` is empty this argument is ignored.
        """
        assert self.aligned()

        start_index = self.bit_tell()
        header_size = 160 + self._METADATA_BIT_SIZE + len(level.sshot) * 8

        self.bit_seek(start_index + header_size)

        # Write variable mapping and record size
        self.write_variable(VariableStruct(level.variables))

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
        self._write_metadata(level)
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
        rmap = _compute_region_map(level)
        region_dir_index = self.bit_tell()
        region_data_index = (region_dir_index + 32 * len(rmap.region_map) + 7) & ~0x7
        self.bit_seek(region_data_index)
        region_offsets = []

        # Write the region data
        for rx, ry in rmap.get_region_keys():
            self.align()
            region_offsets.append((self.bit_tell() - region_data_index) // 8)
            self._write_region(rx, ry, rmap.region_map[(rx, ry)])

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
        """Writes `level` to the output stream. This is equivalent to
        `write_level_ex(level, [], b"")`.

        Arguments:
            level (Level): The level file to write
        """
        self.write_level_ex(level, [], b"")


def write_level(level: Level) -> bytes:
    """Convenience function to write a map file directly to bytes in memory.

    Arguments:
        level (Level): The level file to write

    Returns:
        The bytes that encode that level file
    """
    with DFWriter(io.BytesIO()) as writer:
        writer.write_level(level)
        return writer.data.getvalue()
