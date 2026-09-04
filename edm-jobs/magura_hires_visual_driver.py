import json
import os
import runpy
from pathlib import Path

import bpy

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
PATCH = ROOT / "edm-jobs" / "magura_hires_visual_patch.py"
REFINE = ROOT / "edm-jobs" / "magura_hires_refinement_v2.py"
REPORT = ROOT / "hires-generated" / "visual-qa.json"

# Run the full visual-only mesh/material patch first.
runpy.run_path(str(PATCH), run_name="__main__")

# Apply the close-up QA refinement pass: stern shading, bow seam closure,
# bumper/faceted forward-mesh cleanup. This script includes its own hard
# protected-transform freeze checks.
runpy.run_path(str(REFINE), run_name="__main__")


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
        u = (co[a0] - mins[a0]) / s0
        v = (co[a1] - mins[a1]) / s1
        uv.data[loop.index].uv = (u, v)
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
    if not obj.name.startswith(("HiRes_", "HiResV2_")):
        continue
    if obj.type == "CURVE":
        obj = convert_curve_to_mesh(obj)
        converted.append(obj.name)
    if obj.type == "MESH":
        if ensure_uv(obj):
            fixed.append(obj.name)

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

# Append UV/export-prep QA to the visual report produced by the core/refinement patches.
report = {}
if REPORT.exists():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
report["uv_safe_visual_objects"] = len(fixed)
report["converted_visual_curves"] = converted
report["uv_policy"] = "UVMap guaranteed for every HiRes/HiResV2 mesh; visual curves converted to textured meshes before EDM export"
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(f"MAGURA_HIRES_UV_READY={len(fixed)}")
print(f"MAGURA_HIRES_CURVES_CONVERTED={len(converted)}")
