"""
Module providing methods for reading Dustforce binary formats including map
files.
"""
import functools
import io
from typing import Any, Dict, Tuple
import zlib

from .bitio import BitIOReader
from .entity import Entity
from .enums import LevelType
from .level_map import Map
from .map_exception import MapParseException
from .prop import Prop
from .tile import Tile, TileShape
from .variable import (
    Variable,
    VariableArray,
    VariableBool,
    VariableFloat,
    VariableInt,
    VariableNull,
    VariableString,
    VariableStruct,
    VariableType,
    VariableUInt,
    VariableVec2,
)


class DFReader(BitIOReader):
    """Helper class to read Dustforce binary files"""

    def read_expect(self, data: bytes) -> None:
        """Ensure the next bytes match `data`"""
        if data != self.read_bytes(len(data)):
            raise MapParseException("unexpected data")

    def read_float(self, ibits: int, fbits: int) -> float:
        """Read a float using `ibits` integer bits and `fbits` floating
        point bits"""
        sign = 1 - 2 * self.read(1)
        ipart = self.read(ibits - 1)
        fpart = self.read(fbits)
        return sign * ipart + 1.0 * fpart / (1 << (fbits - 1))

    def read_6bit_str(self) -> str:
        """Read a "6-bit" string"""
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

    def read_var_type(self, vtype: VariableType, allow_continuation=True) -> Variable:
        """Read a variable of a given type"""
        if vtype == VariableType.NULL:
            return VariableNull()
        if vtype == VariableType.BOOL:
            return VariableBool(self.read(1) == 1)
        if vtype == VariableType.UINT:
            return VariableUInt(self.read(32))
        if vtype == VariableType.INT:
            return VariableInt(self.read(32, True))
        if vtype == VariableType.FLOAT:
            return VariableFloat(self.read_float(32, 32))

        if vtype == VariableType.STRING:
            chrs = []
            continuation = True
            while continuation:
                slen = self.read(16)
                chrs.append(self.read_bytes(slen))

                continuation = False
                if allow_continuation and slen == (1 << 16) - 1:
                    # Skip past header data that's there to allow legacy clients to parse
                    # somewhat successfully.
                    continuation = True
                    self.read(4)
                    self.read_6bit_str()

            return VariableString(b"".join(chrs))

        if vtype == VariableType.VEC2:
            f0 = self.read_float(32, 32)
            f1 = self.read_float(32, 32)
            return VariableVec2((f0, f1))

        if vtype == VariableType.ARRAY:
            atype = VariableType(self.read(4))
            alen = self.read(16)
            val = []
            continuation = False
            for _ in range(alen):
                elem = self.read_var_type(atype, False)
                if continuation:
                    val[-1].value += elem.value
                else:
                    val.append(elem)
                continuation = (
                    atype == VariableType.STRING and len(elem.value) == (1 << 16) - 1
                )

            return VariableArray(Variable.TYPES[atype], val)

        if vtype == VariableType.STRUCT:
            return VariableStruct(self.read_var_map())

        raise MapParseException("unknown var type")

    def read_var(self) -> Tuple[str, Variable]:
        """Read a named variable"""
        vtype = VariableType(self.read(4))
        if vtype == VariableType.NULL:
            return None

        var_name = self.read_6bit_str()
        return (var_name, self.read_var_type(vtype))

    def read_var_map(self) -> Dict[str, Variable]:
        """Read a variable mapping"""
        result = {}
        while True:
            var = self.read_var()
            if var is None:
                return result
            result[var[0]] = var[1]

    def read_segment(
        self, mmap: Map, xoffset: int, yoffset: int, config: Dict[str, Any]
    ) -> None:
        """Read a segment into the passed map"""
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
                    xpos = self.read(5)
                    ypos = self.read(5)
                    shape = self.read(8)
                    data = self.read_bytes(12)
                    if shape & 0x80:
                        mmap.tiles[(layer, xoffset + xpos, yoffset + ypos)] = Tile(
                            TileShape(shape & 0x1F), tile_data=data
                        )

        if flags & 2:
            dusts = self.read(10)
            for _ in range(dusts):
                xpos = self.read(5)
                ypos = self.read(5)
                data = self.read_bytes(12)
                tile = mmap.tiles.get((19, xoffset + xpos, yoffset + ypos))
                if tile is not None:
                    tile._set_dust_data(data)

        if flags & 8:
            props = self.read(16)
            for _ in range(props):
                id_num = self.read(32, True)
                if id_num < 0:
                    continue

                layer = self.read(8)
                layer_sub = self.read(8)

                scale = 1
                if version > 6 or config.get("scaled_props"):
                    x_sgn = self.read(1)
                    x_int = self.read(27)
                    x_scale = (self.read(4) & 0x7) ^ 0x4
                    y_sgn = self.read(1)
                    y_int = self.read(27)
                    y_scale = (self.read(4) & 0x7) ^ 0x4

                    xpos = (-1 if x_sgn != 0 else 1) * x_int
                    ypos = (-1 if y_sgn != 0 else 1) * y_int

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

                mmap.props[id_num] = (
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
                variables = self.read_var_map()

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

            # Read in extended names if present and add entities to map
            if has_extended_names:
                self.bit_seek(start_index + (segment_size - 4) * 8)
                extra_names_index = self.read(32)
                self.skip(-extra_names_index - 32)

            for etype, xpos, ypos, eargs, id_num in entities:
                if has_extended_names and etype == "entity":
                    etype = self.read_6bit_str()
                    print("READ EXTENDED NAME", xoffset, yoffset, etype)
                mmap.add_entity(
                    xpos,
                    ypos,
                    Entity._from_raw(etype, *eargs),
                    id_num,
                )

        self.bit_seek(start_index + segment_size * 8)

    def read_region(self, mmap: Map, config: Dict[str, Any]) -> None:
        """Read a region into the passed map"""
        region_len = self.read(32)
        uncompressed_len = self.read(32)  # pylint: disable=unused-variable
        print("rsizes", region_len, uncompressed_len)
        offx = self.read(16, True)
        offy = self.read(16, True)
        print(offx, offy)
        version = self.read(16)  # pylint: disable=unused-variable
        segments = self.read(16)
        has_backdrop = self.read(8) != 0

        sub_reader = DFReader(
            io.BytesIO(zlib.decompress(self.read_bytes(region_len - 17)))
        )
        for _ in range(segments):
            sub_reader.align()
            sub_reader.read_segment(mmap, offx * 256, offy * 256, config)

        if has_backdrop:
            sub_reader.align()
            sub_reader.read_segment(mmap.backdrop, offx * 16, offy * 16, config)

    def read_metadata(self) -> Dict[str, Any]:
        """Read a metadata block (DF_MTD)"""
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
        """Reads a variable mapping with a given header"""
        self.read_expect(header)
        version = self.read(16)  # pylint: disable=unused-variable
        statSize = self.read(32)  # pylint: disable=unused-variable
        return self.read_var_map()

    def read_map(self) -> Map:
        """Reads a map file from the passed data source

        On error raises a MapParseException.
        """
        self.read_expect(b"DF_LVL")

        version = self.read(16)
        if version <= 42:
            raise MapParseException("unsupported level version")

        filesize = self.read(32)  # pylint: disable=unused-variable
        num_regions = self.read(32)
        print(version, filesize, num_regions)
        meta = self.read_metadata()  # pylint: disable=unused-variable

        print(version, filesize, num_regions, meta)

        sshot_data = b""
        if version > 43:
            sshot_len = self.read(32)
            sshot_data = self.read_bytes(sshot_len)

        mmap = Map()
        mmap.variables = self.read_var_map()
        mmap.sshot = sshot_data

        config = {"scaled_props": mmap.level_type == LevelType.DUSTMOD}

        self.align()
        self.skip(num_regions * 32)
        for _ in range(num_regions):
            self.read_region(mmap, config)
        return mmap

    read_stat_file = functools.partial(read_var_file, header=b"DF_STA")
    read_config_file = functools.partial(read_var_file, header=b"DF_CFG")
    read_fog_file = functools.partial(read_var_file, header=b"DF_FOG")


def read_map(data: bytes) -> Map:
    """Convenience method to read in a map from bytes directly"""
    with DFReader(io.BytesIO(data)) as reader:
        return reader.read_map()


# pylint: disable=fixme
# TODO: support DF_EMT, DF_PRT, DF_WND
