from dustmaker.MapReader import read_map
from dustmaker.MapWriter import write_map

class TestDustmaker:
  def test_read_write(self):
    f0 = "/home/msg555/Dustforce/content/levels2/downhill"

    with open(f0, "rb") as f:
      data = bytes(f.read())

    map1 = read_map(data)
    data1 = write_map(map1)
    map2 = read_map(data1)
    data2 = write_map(map2)
    assert data1 != data2
