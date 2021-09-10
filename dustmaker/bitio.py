"""
Module defining the core binary reader for Dustforce binary formats.
"""
import io
import itertools
from typing import BinaryIO, Iterable


class BitIO:
    """Wrapper around a binary IO source that allows integers to be read/written
    to. Reads and writes of integers are all serialized to bits in little
    endian order.

    Within the IO source bits are ordered from LSB to MSB. Therefore the
    first bit of a stream is the '1's place of the first byte. The last bit
    of a stream is the '128's place bit of the last byte.

    Arguments:
        noclose (bool): Normally when the BitIO object is closed
            :attr:`data` is also closed. If this is set then :attr:`data`
            will be left open after this BitIO is closed.
    """

    __slots__ = ("data", "_tell", "_bits", "_bits_left", "_noclose")

    def __init__(self, data: BinaryIO, *, noclose: bool = False) -> None:
        #: BinaryIO: A binary data stream. Should support read/write/seek
        #: if those respective operations are done on the BitIO object itself.
        self.data = data
        self._tell = 0
        self._bits = 0
        self._bits_left = 0
        self._noclose = noclose
        try:
            self._tell = data.tell() << 3
        except (AttributeError, IOError):
            pass

    def release(self) -> None:
        """Prevents :meth:`close` from closing :attr:`data` as well."""
        self._noclose = True

    def close(self) -> None:
        """Flush any pending bits and close :attr:`data` unless
        it has been released.
        """
        if not self._noclose:
            self.data.close()

    def aligned(self) -> bool:
        """Returns True if the stream is aligned at a byte boundary."""
        return self._bits_left == 0

    def align(self) -> None:
        """Seeks the stream forward to the nearest byte boundary. This does
        not require :attr:`data` to support seek itself.
        """
        self._tell += self._bits_left
        self._bits = 0
        self._bits_left = 0

    def skip(self, bits: int) -> None:
        """Skips `bits` bits in the bit stream. Requires :attr:`data` to
        support seeks.

        Arguments:
            bits (int): the number of bits to skip
        """
        self.bit_seek(self._tell + bits)

    def bit_tell(self) -> int:
        """Returns the current bit position of the stream"""
        return self._tell

    def bit_seek(self, pos: int) -> None:
        """Seeks to a new bit-position in the stream.

        Arguments:
            pos (int): The position in bits from the start of the stream
        """
        self.data.seek(pos // 8)
        self._tell = pos
        self._bits_left = -pos % 8
        self._bits = 0 if self._bits_left == 0 else -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class BitIOReader(BitIO):
    """Bit reader wrapper for a data stream"""

    def read(self, bits: int, signed: bool = False) -> int:
        """Reads in the next `bits` bits into an integer in little endian order.

        Arguments:
            bits (int): The number of bits to read in
            signed (bool): Wether the most significant bit should be interpretted
                as a sign bit.
        """
        bytes_needed = (bits - self._bits_left + 7) >> 3
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
        result = self._bits + (int.from_bytes(new_bytes, "little") << self._bits_left)

        # Save the extra data from the last byte
        self._bits = result >> bits
        self._bits_left = (self._bits_left - bits) & 7

        # Remove the extra data
        result = result & (1 << bits) - 1
        if signed and (result & (1 << bits - 1)):
            result -= 1 << bits

        self._tell += bits
        return result

    def read_bytes(self, num: int) -> bytes:
        """Reads in the next `num` bytes and returns them as a `bytes` object.

        Arguments:
            num (int): The number of bytes to extract from the bit stream.
        """
        if self._bits_left == 0:
            data = self.data.read(num)
            self._tell += len(data) << 3
            return data
        return bytes(self.read(8) for _ in range(num))


class BitIOWriter(BitIO):
    """Bit writer wrapper for a data stream."""

    def __init__(self, data: BinaryIO, *, noclose: bool = False) -> None:
        if not isinstance(data, io.BufferedIOBase):
            data = io.BufferedWriter(data)  # type: ignore
        super().__init__(data, noclose=noclose)

    def write(self, bits: int, val: int) -> None:
        """Writes `val`, an integer of `bits` bits in size, to the stream.

        Note:
            If the last byte is partially completed it will not be written
            until the stream is closed or flushed.
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
        full_bytes = (bits - self._bits_left) >> 3
        val_as_bytes = (val >> self._bits_left).to_bytes(full_bytes + 1, "little")
        byte_gen: Iterable[int] = itertools.islice(val_as_bytes, full_bytes)
        if self._bits_left != 0:
            byte_gen = itertools.chain((self._bits,), byte_gen)
        self.data.write(bytes(byte_gen))

        # Fix up our state for leftover bits
        used_bits = (full_bytes << 3) + self._bits_left
        if used_bits == bits:
            self._bits = 0
            self._bits_left = 0
        else:
            self._bits = val_as_bytes[-1]
            self._bits_left = 8 - (bits - used_bits)

        self._tell += bits

    def write_bytes(self, buf: bytes) -> None:
        """Writes the bytes in `buf` to the stream

        Arguments:
            buf (bytes): The data to write to the stream
        """
        if self._bits_left == 0:
            self.data.write(buf)
            self._tell += len(buf) << 3
            return
        for byt in buf:
            self.write(8, byt)

    def close(self) -> None:
        """Flush any pending bits and close the underlying stream
        (unless released).
        """
        try:
            self.flush()
        finally:
            super().close()

    def flush(self) -> None:
        """Flushes any trailing bits.

        Warning:
            If there are trailing bits this will cause the stream to seek
            forward to the next byte boundary. Generally you shouldn't need to
            call this directly and should allow other methods like :meth:`close`,
            :meth:`align`, :meth:`bit_seek` to call flush for you at times that
            always make sense.
        """
        if self._bits_left != 0 and self._bits != -1:
            self.data.write(bytes((self._bits,)))

    def align(self) -> None:
        """Seeks the stream forward to the nearest byte boundary. This does
        not require :attr:`data` to support seek itself. This also triggers
        a flush.
        """
        self.flush()
        super().align()

    # pylint: disable=arguments-differ
    def bit_seek(self, pos: int, *, allow_unaligned: bool = False) -> None:
        """Seeks to the desired position in the stream relative the start.
        This also triggers a flush of any pending data at our current location.

        Arguments:
            pos (int): The bit position to seek to relative the start of the
                stream.
            allow_unaligned (bool): Normally unaligned seeks are not allowed.
                If you set this flag they will be allowed however any write
                performed at the new location will have the effect of zero'ing any
                bits earlier within the byte that we are seeking into.

        Warning:
            Seeking into a non-byte aligned position is not well supported and
            cannot be done generally without performing a read.

        Raises:
            RuntimeError: If seek is not byte aligned and `allow_unaligned` is
                not set.
        """
        if not allow_unaligned and (pos & 7) != 0:
            raise RuntimeError(
                "cannot perform unaligned seek, set allow_unaligned=True if you really want this"
            )
        self.flush()
        super().bit_seek(pos)
