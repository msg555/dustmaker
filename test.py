from MapReader import read_map
from MapWriter import write_map

f0 = "/home/msg555/Dustforce/content/levels2/downhill"
f1 = "/home/msg555/.HitboxTeam/Dustforce/user/level_src/moo"
f2 = "/home/msg555/.HitboxTeam/Dustforce/user/level_src/wut"

with open(f0, "rb") as f:
  data = bytes(f.read())

map = read_map(data)
data = write_map(map)

read_map(data)

#with open(f2, "wb") as f:
#  f.write(data)
