import sys, bpy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpg_station_common import build_station, mats, box
build_station(False)
# Far LOD: preserve recognizable station massing and brand-red canopy only.
keep_prefixes=("FORECOURT","APRON","STORE","STORE_PARAPET","STORE_RED_BAND","CANOPY","CANOPY_RED_FRONT","CANOPY_RED_REAR","COLUMN_","PRICE_POLE","PRICE_BOARD","PRICE_HEADER")
for o in list(bpy.data.objects):
    if not o.name.startswith(keep_prefixes):
        bpy.data.objects.remove(o, do_unlink=True)
M=mats()
box("LOD2_PUMP_MASS_L",(-5.0,-3.2,1.35),(3.2,1.4,2.5),M["white"],.05)
box("LOD2_PUMP_MASS_R",(5.0,-3.2,1.35),(3.2,1.4,2.5),M["white"],.05)
print("[TPG] LOD2 simplified")
