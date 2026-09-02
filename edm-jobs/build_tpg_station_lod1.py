import sys, bpy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpg_station_common import build_station
build_station(False)
# Mid-distance LOD: retain store/canopy/pumps/sign silhouette, remove micro-detail.
for o in list(bpy.data.objects):
    n=o.name
    if any(k in n for k in ("hose","HVAC_SLAT","WIPER","BIN_","DOOR_HANDLE","FRAME_")) or n.startswith("COL_"):
        bpy.data.objects.remove(o, do_unlink=True)
print("[TPG] LOD1 simplified")
