import sys, bpy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpg_station_common import build_station
build_station(False)

# Mid-distance LOD: keep the real four-dispenser layout and primary branding,
# but strip tiny retail clutter/fasteners/text that would shimmer at distance.
micro_tokens=(
    "hose","NOZZLE","HVAC_SLAT","WIPER","DOOR_HANDLE","PRICE_FASTENER",
    "DRAIN_SLAT","KEY_","CAB_BOLT","ANCHOR_","NO_SMOKE","_PAY_","PUSH","AD_",
    "PROPANE_","METER_FACE","A_FRAME_","CANOPY_LIGHT_","SOFFIT_SEAM_","HVAC_1_SCREW",
    "HVAC_2_SCREW","HVAC_3_SCREW","VENT_1_SCREW","VENT_2_SCREW","PARAPET_SCREW"
)
for o in list(bpy.data.objects):
    n=o.name.upper()
    if n.startswith("COL_") or any(t.upper() in n for t in micro_tokens):
        bpy.data.objects.remove(o, do_unlink=True)
print("[TPG] LOD1: four dispensers + architecture retained; micro-detail removed")
