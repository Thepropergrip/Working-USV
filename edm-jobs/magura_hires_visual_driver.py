import json
import os
import runpy
from pathlib import Path

import bpy

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
PATCH = ROOT / "edm-jobs" / "magura_hires_visual_patch.py"
FLATTEN = ROOT / "edm-jobs" / "magura_hires_texture_flatten_v3.py"
REFINE_V3 = ROOT / "edm-jobs" / "magura_hires_refinement_v3.py"
REFINE_V4 = ROOT / "edm-jobs" / "magura_hires_refinement_v4.py"
REPORT = ROOT / "hires-generated" / "visual-qa.json"

# Core visual-only material/launcher detail pass.
runpy.run_path(str(PATCH), run_name="__main__")

# Keep V3 in the chain because it replaces the original low-density bow bumper
# using the original transform/dimensions. V4 then deletes every experimental
# additive helper/detail object and applies the final corrective shading/material
# treatment seen in DCS QA.
runpy.run_path(str(FLATTEN), run_name="__main__")
runpy.run_path(str(REFINE_V3), run_name="__main__")
runpy.run_path(str(REFINE_V4), run_name="__main__")


def ensure_uv(obj):
    if obj.type != "MESH":
        return False
    uv = obj.data.uv_layers.get("UVMap") or obj.data.uv_layers.new(name="UVMap")
    uv.active = True
    uv.active_render = True
    if not obj.data.vertices or not obj.data.loops:
        return True
    coords = [v.co for v in obj.data.vertices]
    mins = [min(c[a] for c in coords) for a in range(3)]
    maxs = [max(c[a] for c in coords) for a in range(3)]
    spans = [maxs[a] - mins[a] for a in range(3)]
    axes = sorted(range(3), key=lambda a: spans[a], reverse=True)[:2]
    a0, a1 = axes
    s0 = spans[a0] if spans[a0] > 1.0e-6 else 1.0
    s1 = spans[a1] if spans[a1] > 1.0e-6 else 1.0
    for loop in obj.data.loops:
        co = obj.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((co[a0] - mins[a0]) / s0, (co[a1] - mins[a1]) / s1)
    return True


def convert_curve_to_mesh(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    return obj

fixed = []
converted = []
for obj in list(bpy.data.objects):
    if not obj.name.startswith(("HiRes_", "HiResV3_", "HiResV4_")):
        continue
    if obj.type == "CURVE":
        obj = convert_curve_to_mesh(obj)
        converted.append(obj.name)
    if obj.type == "MESH" and ensure_uv(obj):
        fixed.append(obj.name)

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

report = {}
if REPORT.exists():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
report["uv_safe_visual_objects"] = len(fixed)
report["converted_visual_curves"] = converted
report["uv_policy"] = "UVMap guaranteed for every surviving HiRes/V3/V4 visual mesh before EDM export"
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(f"MAGURA_HIRES_UV_READY={len(fixed)}")
print(f"MAGURA_HIRES_CURVES_CONVERTED={len(converted)}")
