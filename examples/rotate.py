from dustmaker import *

f0 = "/home/msg555/Dustforce/content/levels2/downhill"
f1 = "/home/msg555/.HitboxTeam/Dustforce/user/level_src/test"

with open(f0, "rb") as f:
    map = read_map(f.read())

# Rotate the map 90 degrees.
map.rotate()

# Remove the key from the map.
map.vars["key_get_type"] = Var(VarType.UINT, 0)

# Rename the map
map.name("Downhill Rotated")

# Remove camera nodes as they don't work well.
for (id, (x, y, entity)) in list(map.entities.items()):
    if isinstance(entity, CameraNode):
        del map.entities[id]

# Write out the final version.
with open(f1, "wb") as f:
    f.write(write_map(map))
