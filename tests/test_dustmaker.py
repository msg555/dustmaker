from dustmaker.MapReader import read_map
from dustmaker.MapWriter import write_map

import os

here = os.path.abspath(os.path.dirname(__file__))

class TestDustmaker:
  def test_read_write(self):
    f_in = os.path.join(here, "downhill")

    with open(f_in, "rb") as f:
      data = bytes(f.read())

    map1 = read_map(data)
    data1 = write_map(map1)
    map2 = read_map(data1)
    data2 = write_map(map2)
    assert data1 != data2
