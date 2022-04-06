"""
End to end tests for Dustmaker as a whole
"""
import io
import os
import unittest

from dustmaker import (
    read_level,
    write_level,
    DFReader,
    DFWriter,
)

here = os.path.abspath(os.path.dirname(__file__))


class TestEndToEnd(unittest.TestCase):
    """
    End to end tests for Dustmaker.
    """

    def test_read_write(self):
        """Test read/write cycles succeed and produce a fixed result"""
        f_in = os.path.join(here, "downhill")

        with open(f_in, "rb") as f:
            data = bytes(f.read())

        level1 = read_level(data)
        data1 = write_level(level1)

        with DFReader(io.BytesIO(data1)) as reader:
            level2 = reader.read_level()

        with DFWriter(io.BytesIO()) as writer:
            writer.write_level(level2)
            writer.flush()
            data2 = writer.data.getvalue()

        self.assertEqual(data1, data2)

        with DFReader(io.BytesIO(data2)) as reader:
            level3, region_offsets = reader.read_level_ex()
            region_data = reader.read_bytes(region_offsets[-1])

        with DFWriter(io.BytesIO()) as writer:
            writer.write_level_ex(level3, region_offsets, region_data)
            data3 = writer.data.getvalue()
            self.assertEqual(data1, data3)

    def test_read_write_replay(self):
        """Test read/write cycles succeed and produce a fixed result on a replay"""
        f_in = os.path.join(here, "downhill.dfreplay")

        with DFReader(open(f_in, "rb")) as reader:
            replay1 = reader.read_replay()

        with DFWriter(io.BytesIO()) as writer:
            writer.write_replay(replay1)
            writer.flush()
            data1 = writer.data.getvalue()

        with DFReader(io.BytesIO(data1)) as reader:
            replay2 = reader.read_replay()

        with DFWriter(io.BytesIO()) as writer:
            writer.write_replay(replay2)
            writer.flush()
            data2 = writer.data.getvalue()

        self.assertEqual(data1, data2)
