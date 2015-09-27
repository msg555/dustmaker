class BitWriter:
  def __init__(self):
    self.pos = 0
    self.data = bytearray()

  def write(self, bits, val):
    if val < 0:
      val += 1 << bits

    off = self.pos & 0x7
    self.pos += bits
    if off != 0:
      cnt = min(8 - off, bits)
      self.data[-1] |= (val & ((1 << cnt) - 1)) << off
      bits -= cnt
      val = val >> cnt

    while bits >= 8:
      self.data.append(val & 0xFF)
      val = val >> 8
      bits -= 8

    if bits != 0:
      self.data.append(val & ((1 << bits) - 1))

  def bytes(self):
    return bytes(self.data)

  def byte_count(self):
    return len(self.data)

  def align(self, size = 8):
    self.pos += (size - self.pos % size) % size
    while len(self.data) * 8 < self.pos:
      self.data.append(0)

  def write_bytes(self, data):
    if (self.pos & 7) == 0:
      self.data += data
      self.pos += 8 * len(data)
    else:
      for x in data:
        self.write(8, x)
