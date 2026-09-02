import sys, bpy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpg_station_common import build_station, mats, box
build_station(False)

# Far LOD: recognizable massing only. Keep four separate pump masses so the
# station still reads as a four-pump facility instead of collapsing to two blobs.
keep_prefixes=(
    "FORECOURT","APRON","STORE","STORE_PARAPET","STORE_RED_BAND",
    "CANOPY","CANOPY_RED_FRONT","CANOPY_RED_REAR","CANOPY_SIDE_",
    "COLUMN_","PRICE_CABINET","PRICE_HEADER","PRICE_POST_","PRICE_FOOT_"
)
for o in list(bpy.data.objects):
    if o.name.startswith("COL_"):
        bpy.data.objects.remove(o, do_unlink=True)
        continue
    if not o.name.startswith(keep_prefixes):
        bpy.data.objects.remove(o, do_unlink=True)

M=mats()
for i,x in enumerate((-7.5,-2.5,2.5,7.5),1):
    box(f"LOD2_PUMP_{i}",(x,-3.35,1.30),(1.15,.85,2.45),M["white"],.04)
print("[TPG] LOD2: architecture, pylon and four pump silhouettes retained")
