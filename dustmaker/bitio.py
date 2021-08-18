"""
Module defining the core binary reader for Dustforce binary formats.
"""
import itertools
from typing import BinaryIO, Iterable


class BitIO:
    """Wrapper around a binary IO source that allows integers to be read/written
    to. Reads and writes of integers are all serialized to bits in little
    endian order.

    Within the IO source bits are ordered from LSB to MSB. Therefore the
    first bit is the '1's place of the first byte and the last bit is the
    '128's place of the last byte.
    """

    def __init__(self, data: BinaryIO) -> None:
        """Create a new BitIO using data as the backing stream.

        data - A binary input stream. Should support read/write/seek if those
            respective operations are done on the BitIO itself.
        """
        self.data = data
        self._tell = 0
        self._bits = 0
        self._bits_left = 0
        try:
            self._tell = data.tell()
        except (AttributeError, IOError):
            pass

    def close(self) -> None:
        """Flush any pending bits and close the underlying stream."""
        self.data.close()

    def aligned(self) -> bool:
        """Returns True if the stream is aligned at a byte boundary."""
        return self._bits_left == 0

    def align(self) -> None:
        """Seeks the stream forward to the nearest byte boundary. This does
        not require the underlying data stream to support seek.
        """
        self._tell += self._bits_left
        self._bits = 0
        self._bits_left = 0

    def skip(self, bits: int) -> None:
        """Skips `bits` bits in the bit stream.

        bits -- the number of bits to skip.
        """
        self.bit_seek(self._tell + bits)

    def bit_tell(self) -> int:
        """Returns the current bit position of the stream"""
        return self._tell

    def bit_seek(self, pos: int) -> None:
        """Seeks to the desired position in the stream relative the start"""
        self.data.seek(pos // 8)
        self._tell = pos
        self._bits_left = -pos % 8
        self._bits = 0 if self._bits_left == 0 else -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.data.close()


class BitIOReader(BitIO):
    """
    Bit reader wrapper for a data stream.
    """

    def read(self, bits, signed=False) -> int:
        """Reads the next `bits` bits into an integer in little endian order.

        bits -- The number of bits to read.
        signed -- Indicates if the MSB is a sign bit.
        """
        bytes_needed = (bits - self._bits_left + 7) // 8
        if self._bits == -1:
            # We did a seek mid-byte and need to read the lead byte still.
            bytes_needed += 1

        if bytes_needed == 0:
            # No need to actually read
            result = self._bits & (1 << bits) - 1
            self._bits = self._bits >> bits
            self._bits_left -= bits
            self._tell += bits
            return result

        # Read in needed data from underlying stream.
        new_bytes = self.data.read(bytes_needed)

        if self._bits == -1:
            self._bits = new_bytes[0] >> (8 - self._bits_left)
            new_bytes = new_bytes[1:]

        # Calculate the result with maybe some extra data from the last byte.
        result = self._bits + sum(
            byt << (i * 8 + self._bits_left) for i, byt in enumerate(new_bytes)
        )

        # Save the extra data from the last byte
        self._bits = result >> bits
        self._bits_left = (self._bits_left - bits) % 8

        # Remove the extra data
        result = result & (1 << bits) - 1
        if signed and (result & (1 << bits - 1)):
            result -= 1 << bits

        self._tell += bits
        return result

    def read_bytes(self, num: int) -> bytes:
        """Returns a bytes object containing the next `num` bytes from the bit
        stream.

        num -- The number of bytes to extract from the bit stream.
        """
        if self._bits_left == 0:
            data = self.data.read(num)
            self._tell += len(data) * 8
            return data
        return bytes(self.read(8) for _ in range(num))


class BitIOWriter(BitIO):
    """
    Bit writer wrapper for a data stream.
    """

    def write(self, bits: int, val: int) -> None:
        """Writes `val`, an integer of `bits` bits in size, to the stream.

        Partially written bits will not be written to the stream until it is
        closed or flush is called.

        Seeks mid-byte are not supported and will cause data loss if a write is
        attempted. Writes in the middle of the data stream that do not align to
        a byte boundary are similarly not supported and will cause data loss.
        """
        if val < 0:
            val += 1 << bits

        if self._bits == -1:
            # Mid seek write will lose data.
            self._bits = 0

        # Fill in the missing bits of the lead byte
        if self._bits_left != 0:
            lead_val = val & (1 << self._bits_left) - 1
            self._bits |= lead_val << (8 - self._bits_left)

        if bits < self._bits_left:
            self._bits_left -= bits
            self._tell += bits
            return

        # Figure out what bytes need to be written to the stream
        full_bytes = (bits - self._bits_left) // 8
        byte_gen: Iterable[int] = (
            (val >> (i * 8 + self._bits_left)) & 0xFF for i in range(full_bytes)
        )
        if self._bits_left != 0:
            byte_gen = itertools.chain((self._bits,), byte_gen)
        self.data.write(bytes(byte_gen))

        # Fix up our state for leftover bits
        used_bits = full_bytes * 8 + self._bits_left
        if used_bits == bits:
            self._bits = 0
            self._bits_left = 0
        else:
            self._bits = val >> used_bits
            self._bits_left = 8 - (bits - used_bits)

        self._tell += bits

    def write_bytes(self, buf: bytes) -> None:
        """Writes the bytes in buf to the stream"""
        if self._bits_left == 0:
            self.data.write(buf)
            self._tell += len(buf) * 8
            return
        for byt in buf:
            self.write(8, byt)

    def close(self) -> None:
        """Flush any pending bits and close the underlying stream."""
        try:
            self._flush()
        finally:
            super().close()

    def _flush(self) -> None:
        """Flushes any trailing bits. As a side effect seeks the data stream
        forward."""
        if self._bits_left != 0 and self._bits != -1:
            self.data.write(bytes((self._bits,)))

    def align(self) -> None:
        """Seeks the stream forward to the nearest byte boundary. This does
        not require the underlying data stream to support seek. This also
        triggers a flush.
        """
        self._flush()
        super().align()

    # pylint: disable=arguments-differ
    def bit_seek(self, pos: int, *, allow_unaligned: bool = False) -> None:
        """Seeks to the desired position in the stream relative the start.
        This also triggers a flush.
        """
        if not allow_unaligned and pos % 8 != 0:
            raise RuntimeError(
                "cannot perform unaligned seek, set allow_unaligned=True if you really want this"
            )
        self._flush()
        super().bit_seek(pos)
