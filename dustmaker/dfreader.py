""" Module providing methods for reading Dustforce binary formats including
level files.
"""
import io
from typing import Any, Dict, List, Tuple
import zlib

from .bitio import BitIOReader
from .entity import Entity
from .level import Level, LevelType
from .exceptions import LevelParseException
from .prop import Prop
from .tile import Tile, TileShape
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


class DFReader(BitIOReader):
    """Helper class to read Dustforce binary files"""

    def read_expect(self, data: bytes) -> None:
        """Ensure the next bytes match `data`

        Raises:
            LevelParseException: If the read bytes do not match `data`.
        """
        if data != self.read_bytes(len(data)):
            raise LevelParseException("unexpected data")

    def read_float(self, ibits: int, fbits: int) -> float:
        """Read a float in the Dustforce format

        Arguments:
            ibits (int): Number of integer bits
            fbits (int): Number of fractional bits
        """
        sign = 1 - 2 * self.read(1)
        ipart = self.read(ibits - 1)
        fpart = self.read(fbits)
        return sign * ipart + 1.0 * fpart / (1 << (fbits - 1))

    def read_6bit_str(self) -> str:
        """Read a '6-bit' string. These are strings with length between
        0 and 63 inclusive that contain only alpha-numeric lower and uppercase
        characters in addition to '_' and '{'.
        """
        ln = self.read(6)
        chrs = []
        for _ in range(ln):
            v = self.read(6)
            if v < 10:
                chrs.append(chr(ord("0") + v))
            elif v < 36:
                chrs.append(chr(ord("A") + v - 10))
            elif v == 36:
                chrs.append("_")
            elif v < 63:
                chrs.append(chr(ord("a") + v - 37))
            else:
                chrs.append("{")
        return "".join(chrs)

    def read_variable(self, vtype: VariableType) -> Variable:
        """Read a variable of a given type.

        Arguments:
            vtype (VariableType): The type of variable to read
        """
        max_width = (2 ** 16) - 1
        if vtype == VariableType.NULL:
            raise LevelParseException("unexpected null variable")
        if vtype == VariableType.BOOL:
            return VariableBool(self.read(1) == 1)
        if vtype == VariableType.UINT:
            return VariableUInt(self.read(32))
        if vtype == VariableType.INT:
            return VariableInt(self.read(32, True))
        if vtype == VariableType.FLOAT:
            return VariableFloat(self.read_float(32, 32))

        if vtype == VariableType.STRING:
            slen = self.read(16)
            return VariableString(self.read_bytes(slen))

        if vtype == VariableType.VEC2:
            f0 = self.read_float(32, 32)
            f1 = self.read_float(32, 32)
            return VariableVec2((f0, f1))

        if vtype == VariableType.ARRAY:
            atype = VariableType(self.read(4))
            alen = self.read(16)
            val: List[Variable] = []

            if atype != VariableType.STRING:
                val.extend(self.read_variable(atype) for _ in range(alen))
            else:
                while alen > 0:
                    var_value_ctns = []
                    while alen > 0:
                        alen -= 1
                        value_part = self.read_variable(atype).value
                        var_value_ctns.append(value_part)
                        if len(value_part) < max_width:
                            break

                    val.append(VariableString(b"".join(var_value_ctns)))

            return VariableArray(Variable._TYPES[atype], val)

        if vtype == VariableType.STRUCT:
            result: Dict[str, Variable] = {}
            while True:
                vtype = VariableType(self.read(4))
                if vtype == VariableType.NULL:
                    break

                var_name = self.read_6bit_str()
                if vtype != VariableType.STRING:
                    result[var_name] = self.read_variable(vtype)
                    continue

                var_value_ctns = []
                while True:
                    value_part = self.read_variable(vtype)
                    var_value_ctns.append(value_part.value)
                    if len(value_part.value) < max_width:
                        break

                    self.read(4)
                    self.read_6bit_str()

                result[var_name] = VariableString(b"".join(var_value_ctns))

            return VariableStruct(result)

        raise LevelParseException("unknown var type")

    def read_variable_map(self) -> Dict[str, Variable]:
        """Convenience method equivalent to `read_variable(VariableType.STRUCT).value`"""
        return self.read_variable(VariableType.STRUCT).value

    def read_segment(self, level: Level, xoffset: int, yoffset: int) -> None:
        """Read segment data into the passed level. In most cases you should
        just use :meth:`read_level` instead of this method.

        Arguments:
            level (Level): The level object to read data into
            xoffset (int): The segment x-offset in tiles
            yoffset (int): The segment y-offset in tiles
        """
        start_index = self.bit_tell()

        segment_size = self.read(32)
        version = self.read(16)
        xoffset += self.read(8) * 16
        yoffset += self.read(8) * 16
        segment_width = self.read(8)  # pylint: disable=unused-variable

        if version > 4:
            level_uid = self.read(32)  # pylint: disable=unused-variable
            dust_filth = self.read(16)  # pylint: disable=unused-variable
            enemy_filth = self.read(16)  # pylint: disable=unused-variable
        if version > 5:
            tile_surface = self.read(16)  # pylint: disable=unused-variable
            dustblock_filth = self.read(16)  # pylint: disable=unused-variable

        flags = self.read(32)
        if flags & 1:
            layers = self.read(8)
            for _ in range(layers):
                layer = self.read(8)
                tiles = self.read(10)

                for _ in range(tiles):
                    txpos = self.read(5)
                    typos = self.read(5)
                    shape = self.read(5)
                    tile_flags = self.read(3)
                    data = self.read_bytes(12)
                    level.tiles[(layer, xoffset + txpos, yoffset + typos)] = Tile(
                        TileShape(shape & 0x1F),
                        tile_flags=tile_flags,
                        _tile_data=data,
                    )

        if flags & 2:
            dusts = self.read(10)
            for _ in range(dusts):
                txpos = self.read(5)
                typos = self.read(5)
                data = self.read_bytes(12)
                tile = level.tiles.get((19, xoffset + txpos, yoffset + typos))
                if tile is not None:
                    tile._unpack_dust_data(data)

        if flags & 8:
            props = self.read(16)
            for _ in range(props):
                id_num = self.read(32, True)
                if id_num < 0:
                    continue

                layer = self.read(8)
                layer_sub = self.read(8)

                scale = 1.0
                if version > 6 or level.level_type == LevelType.DUSTMOD:
                    x_sgn = self.read(1)
                    x_int = self.read(27)
                    x_scale = (self.read(4) & 0x7) ^ 0x4
                    y_sgn = self.read(1)
                    y_int = self.read(27)
                    y_scale = (self.read(4) & 0x7) ^ 0x4

                    xpos = (-1.0 if x_sgn != 0 else 1.0) * x_int
                    ypos = (-1.0 if y_sgn != 0 else 1.0) * y_int

                    scale_lg = x_scale * 7 + y_scale
                    scale = pow(50.0, (scale_lg - 32.0) / 24.0)
                else:
                    xpos = self.read_float(28, 4)
                    ypos = self.read_float(28, 4)

                rotation = self.read(16)
                flip_x = self.read(1) != 0
                flip_y = self.read(1) != 0
                prop_set = self.read(8)
                prop_group = self.read(12)
                prop_index = self.read(12)
                palette = self.read(8)

                # Default DF behavior is to overwrite repeated props
                level.props.pop(id_num, None)
                level.add_prop(
                    layer,
                    xpos,
                    ypos,
                    Prop(
                        layer_sub,
                        rotation,
                        flip_x,
                        flip_y,
                        scale,
                        prop_set,
                        prop_group,
                        prop_index,
                        palette,
                    ),
                    id_num=id_num,
                )

        if flags & 4:
            entities = []
            num_entities = self.read(16)
            has_extended_names = False
            for _ in range(num_entities):
                id_num = self.read(32, True)
                if id_num < 0:
                    continue

                etype = self.read_6bit_str()
                if etype == "entity" and version > 7:
                    has_extended_names = True
                xpos = self.read_float(32, 8)
                ypos = self.read_float(32, 8)
                rotation = self.read(16)
                layer = self.read(8)
                faceX = self.read(1)
                faceY = self.read(1)
                visible = self.read(1)
                variables = self.read_variable_map()

                entities.append(
                    (
                        etype,
                        xpos,
                        ypos,
                        (
                            variables,
                            rotation,
                            layer,
                            faceX == 0,
                            faceY == 0,
                            visible == 1,
                        ),
                        id_num,
                    )
                )

            # Read in extended names if present and add entities to level
            if has_extended_names:
                self.bit_seek(start_index + (segment_size - 4) * 8)
                extra_names_index = self.read(32)
                self.skip(-extra_names_index - 32)

            for etype, xpos, ypos, eargs, id_num in entities:
                if has_extended_names and etype == "entity":
                    etype = self.read_6bit_str()
                level.entities.pop(id_num, None)
                level.add_entity(
                    xpos,
                    ypos,
                    Entity._from_raw(etype, *eargs),
                    id_num,
                )

        self.bit_seek(start_index + segment_size * 8)

    def read_region(self, level: Level) -> None:
        """Read region data into the passed level. In most cases you should
        just use :meth:`read_level` instead of this method.

        Arguments:
            level (Level): The level object to read data into
        """
        region_len = self.read(32)
        uncompressed_len = self.read(32)  # pylint: disable=unused-variable
        offx = self.read(16, True)
        offy = self.read(16, True)
        version = self.read(16)  # pylint: disable=unused-variable
        segments = self.read(16)
        has_backdrop = self.read(8) != 0

        sub_reader = DFReader(
            io.BytesIO(zlib.decompress(self.read_bytes(region_len - 17)))
        )
        for _ in range(segments):
            sub_reader.align()
            sub_reader.read_segment(level, offx * 256, offy * 256)

        if has_backdrop:
            if level.backdrop is None:
                raise ValueError("no backdrop present in level")
            sub_reader.align()
            sub_reader.read_segment(level.backdrop, offx * 16, offy * 16)

    def _read_metadata(self) -> Dict[str, Any]:
        """Read a metadata block (DF_MTD) into a JSON payload."""
        self.read_expect(b"DF_MTD")

        version = self.read(16)
        region_offset = self.read(32)  # pylint: disable=unused-variable
        entityUid = self.read(32)
        propUid = self.read(32)
        deprecatedSaveUid = self.read(32)
        regionUidDeprecated = self.read(32)
        return {
            "version": version,
            "entityUid": entityUid,
            "propUid": propUid,
            "deprecatedSaveUid": deprecatedSaveUid,
            "regionUidDeprecated": regionUidDeprecated,
        }

    def read_var_file(self, header: bytes) -> Dict[str, Variable]:
        """Reads a variable mapping with a given header. There are several
        file types that Dustforce use that are expressed this way including
        notably "stats1" (header=b"DF_STA") and "config" (header=b"DF_CFG").

        Arguments:
            header (bytes): The expected file header at the start of the stream.
                Just pass b"" if you've already read and checked the header.
        """
        self.read_expect(header)
        version = self.read(16)  # pylint: disable=unused-variable
        statSize = self.read(32)  # pylint: disable=unused-variable
        return self.read_variable_map()

    def read_level_ex(self) -> Tuple[Level, List[int]]:
        """Extended version of :meth:`read_level`.

        Read level file metadata into a :class:`Level` object while
        extracting additional metadata so that the rest of the data can be
        ingested in an opaque way. `read_level_ex` ends with the reader
        byte-aligned. The entirety of the region data can be read subsequently
        with reader.read_bytes(region_bytes) or using :meth:`read_region`.

        This can be used with :meth:`dustmaker.dfwriter.DFWriter.write_level_ex` to modify
        level metadata without reading in region data.

        Example: ::

            # Re-write level metadata without reading in region data.
            level, region_offsets = reader.read_level_ex()
            region_data = reader.read_bytes(region_offsets[-1])
            ...
            writer.write_level_ex(level, region_offsets, region_data)

        Example: ::

            # Manually read region data
            level, region_offsets = reader.read_level_ex()
            for _ in region_offsets[:-1]:
                reader.read_region(level)

        Returns:
            (level, region_offsets) tuple

            - level
                :class:`dustmaker.level.Level` object with metadata (e.g.
                level.variables and level.sshot) filled in.
            - region_offsets
                list of byte offsets of each region from the current stream position
                (which is aligned). The last element of this array is the end of the
                region data and does not correspond to a region itself.
        """
        assert self.aligned()
        start_index = self.bit_tell()
        self.read_expect(b"DF_LVL")

        version = self.read(16)
        if version <= 42:
            raise LevelParseException("unsupported level version")

        filesize = self.read(32)  # pylint: disable=unused-variable
        num_regions = self.read(32)
        meta = self._read_metadata()  # pylint: disable=unused-variable

        sshot_data = b""
        if version > 43:
            sshot_len = self.read(32)
            sshot_data = self.read_bytes(sshot_len)

        level = Level()
        level._next_id = meta["entityUid"]
        level.variables = self.read_variable_map()
        level.sshot = sshot_data

        region_offsets = [self.read(32) for _ in range(num_regions)]
        self.align()

        region_offsets.append(filesize - ((self.bit_tell() - start_index) >> 3))
        return level, region_offsets

    def read_level(self, *, metadata_only: bool = False) -> Level:
        """Read a level data stream and return the :class:`dustmaker.level.Level`
        object.

        Arguments:
            metadata_only (bool, optional): If set to True only the variables
                and sshot data will be set in the returned :class:`Level`.

        Raises:
            LevelParseException: Parser ran into unexpected data.
        """
        level, region_offsets = self.read_level_ex()
        if metadata_only:
            return level

        for _ in range(len(region_offsets) - 1):
            self.read_region(level)
        return level


def read_level(data: bytes) -> Level:
    """Convenience function to read in a level from bytes directly

    Arguments:
        data (bytes): The data source for the level

    Returns:
        The parsed Level object.
    """
    with DFReader(io.BytesIO(data), noclose=True) as reader:
        return reader.read_level()
