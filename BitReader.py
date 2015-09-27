class BitReader:
  def __init__(self, data):
    self.pos = 0
    self.data = data

  def read(self, bits, signed = False):
    result = 0

    ind = self.pos >> 3
    off = self.pos & 0x7
    if off != 0:
      result = self.data[ind] >> off
      ind += 1

    shift = (8 - off) & 0x7
    while shift < bits:
      result |= self.data[ind] << shift
      ind += 1
      shift += 8

    result &= (1 << bits) - 1
    if signed and (result & (1 << bits - 1)) != 0:
      result -= 1 << bits
    self.pos += bits

    return result

  def align(self, size = 8):
    self.pos += (size - self.pos % size) % size

  def skip(self, bits):
    self.pos += bits

  def more(self):
    return self.pos < len(self.data) * 8

  def read_bytes(self, num):
    if (self.pos & 7) == 0:
      result = self.data[self.pos >> 3 : (self.pos >> 3) + num]
      self.pos += num * 8
    else:
      result = bytearray()
      for i in range(num):
        result.append(self.read(8))
      result = bytes(result)
    return result
