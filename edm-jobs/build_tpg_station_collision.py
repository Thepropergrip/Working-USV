import bpy, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpg_station_common import mats, box
from objects_custom_props import get_edm_props

M = mats()
C = M["charcoal"]

def coll_box(name, loc, scale, bevel=0.0):
    o = box(name, loc, scale, C, bevel, True)
    o.hide_render = False
    return o

# Placement-friendly collision shell.
# Intentionally NO horizontal canopy roof/deck collision surface.
# Terrain remains the placement surface beneath the fueling area.

# Convenience store solid volume.
coll_box("COL_STORE",(0,8.0,2.10),(17.4,7.4,4.2))

# Six canopy support columns only. The visible canopy remains in the render EDM.
for x in (-10.6,0,10.6):
    for y in (-7.9,1.25):
        coll_box("COL_COLUMN_"+str(x)+"_"+str(y),(x,y,2.58),(.58,.58,5.16))

# Four pump islands/cabinets.
for x in (-7.5,-2.5,2.5,7.5):
    coll_box("COL_PUMP_ISLAND_"+str(x),(x,-3.35,.18),(2.95,1.42,.36))
    coll_box("COL_PUMP_"+str(x),(x,-3.35,1.36),(1.18,.88,2.48))

# Roadside sign and air/vac equipment.
coll_box("COL_SIGN",(-14.7,7.8,4.8),(4.6,.68,7.7))
coll_box("COL_AIRVAC",(10.4,3.4,.95),(1.2,.9,1.9))

print("[TPG] Placement-friendly collision shell built without canopy roof collision.")
