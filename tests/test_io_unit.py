"""
Unit tests for IO routines
"""
import io
import random
import unittest

from dustmaker import DFReader, DFWriter
from dustmaker.variable import (
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


class TestIOUnit(unittest.TestCase):
    """
    Unit tests for dustmaker
    """

    def test_6bit_str(self):
        """Test writing and reading 6bit strings"""
        alpha = "abcdefghijklmnopqrstuvwxyz"
        numeric = "0123456789"
        options = "_{" + alpha + alpha.upper() + numeric
        assert len(options) == 64

        # Test writing and reading a fixed string gives the expected values.
        expected_text = "Hello_Wor{d"
        expected_data = b"K\x94\xc2\xf0L\x82\xb3\xfd\xa3"
        with DFWriter(io.BytesIO()) as writer:
            writer.write_6bit_str(expected_text)
            self.assertEqual(expected_data, writer.data.getvalue())

        with DFReader(io.BytesIO(expected_data)) as reader:
            self.assertEqual(expected_text, reader.read_6bit_str())

        # Test that writing and then reading random data produces the original input.
        write_data = []
        rng = random.Random(555)
        with DFWriter(io.BytesIO()) as writer:
            for i in range(64 * 2):
                writer.write(1, 1)

                text = "".join(rng.choices(options, k=i % 64))
                write_data.append((writer.bit_tell(), text))
                writer.write_6bit_str(text)

            wdata = writer.data.getvalue()

        with DFReader(io.BytesIO(wdata)) as reader:
            # Test reading data in order
            for _, text in write_data:
                self.assertEqual(1, reader.read(1))
                self.assertEqual(text, reader.read_6bit_str())

            # Test random seek reads
            rng.shuffle(write_data)
            for pos, text in write_data:
                reader.bit_seek(pos)
                self.assertEqual(text, reader.read_6bit_str())

    def test_var_io(self):
        """Test that variables get serialized correctly"""
        variables = VariableStruct(
            {
                "v1": VariableBool(False),
                "v2": VariableBool(False),
                "a" * 63: VariableInt(-(2**31)),
                "b": VariableUInt((2**32) - 1),
                "longstring": VariableString(b"wowee" * (2**16)),
                "arr": VariableArray(
                    VariableString,
                    [
                        VariableString(b"hi"),
                        VariableString(b"bye"),
                        VariableString(b"nice" * (2**16)),
                        VariableString(b"later"),
                    ],
                ),
                "emptyarr": VariableArray(VariableInt, []),
                "structarr": VariableArray(
                    VariableStruct,
                    [
                        VariableStruct({"key1": VariableFloat(0.5)}),
                        VariableStruct({"key2": VariableInt(555)}),
                    ],
                ),
                "emptystruct": VariableStruct({}),
                "vec2": VariableVec2((2.0, 4.0)),
            }
        )

        with DFWriter(io.BytesIO()) as writer:
            writer.write_variable(variables)
            writer.flush()
            data = writer.data.getvalue()

        with DFReader(io.BytesIO(data)) as reader:
            variables_new = reader.read_variable(VariableType.STRUCT)

        self.assertEqual(variables, variables_new)
