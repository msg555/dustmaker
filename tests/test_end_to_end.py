"""
End to end tests for Dustmaker as a whole
"""
import os
import unittest

from dustmaker import read_map, write_map

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

        map1 = read_map(data)
        data1 = write_map(map1)
        map2 = read_map(data1)
        data2 = write_map(map2)
        self.assertEqual(data1, data2)
