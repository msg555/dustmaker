"""
Unit tests for IO routines
"""
import io
import random
import unittest

from dustmaker import DFReader, DFWriter


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
