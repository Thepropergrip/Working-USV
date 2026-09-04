import bpy
import addon_utils
import math
import os
import sys
from pathlib import Path

# Legacy DCS EDM v10 light-only overlay.
# Uses the pre-official Blender EDM exporter model::LightNode v1 encoding,
# matching the generation used by known working dynamic-light static assets.

YARD_RISE = 0.4572
LIGHTS = [
    (-50.0, -31.0, 8.0 + YARD_RISE),
    (-32.0, -31.0, 8.0 + YARD_RISE),
    (-10.0, -31.0, 8.0 + YARD_RISE),
    ( 12.0, -31.0, 8.0 + YARD_RISE),
    ( 34.0, -31.0, 8.0 + YARD_RISE),
    ( 51.0, -18.0, 8.0 + YARD_RISE),
    ( 51.0,   6.0, 8.0 + YARD_RISE),
    ( 51.0,  28.0, 8.0 + YARD_RISE),
    (-50.0,  30.0, 8.0 + YARD_RISE),
]


def arg_value(flag, default=None):
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


out_path = Path(arg_value("--out", "TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS.edm")).resolve()
out_path.parent.mkdir(parents=True, exist_ok=True)

# Enable the legacy exporter installed by the workflow.
addon_utils.enable("io_BlenderEdmExporter", default_set=False, persistent=False)

# Clean scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.armatures):
    pass

# The legacy exporter requires exactly one exported armature and exactly one root bone.
arm_data = bpy.data.armatures.new("TPG_LEGACY_LIGHT_ROOT_ARM")
arm_obj = bpy.data.objects.new("TPG_LEGACY_LIGHT_ROOT", arm_data)
bpy.context.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj
arm_obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
root = arm_data.edit_bones.new("Root")
root.head = (0.0, 0.0, 0.0)
root.tail = (0.0, 0.0, 1.0)
bpy.ops.object.mode_set(mode="OBJECT")

# Explicit generous bounds eliminate the invalid-bounds failure that light-only
# models can otherwise trigger in DCS.
arm_data.EDMAutoCalcBoxes = False
arm_data.EDMUserBoxMin = (-60.0, -42.0, -1.5)
arm_data.EDMUserBoxMax = ( 60.0,  42.0, 12.0)
arm_data.EDMBoundingBoxMin = (-60.0, -42.0, -1.5)
arm_data.EDMBoundingBoxMax = ( 60.0,  42.0, 12.0)

# Legacy Omni lights are intentional for the first real illumination build:
# unlike the modern Lua/projector attempts, an omni source does not depend on
# connector orientation. Each elevated source should visibly illuminate terrain,
# the substation geometry, and nearby vehicles if DCS accepts LightNode v1.
for i, (x, y, z) in enumerate(LIGHTS):
    light = bpy.data.objects.new(f"TPG_LEGACY_DYN_LIGHT_{i:02d}", None)
    bpy.context.collection.objects.link(light)
    light.parent = arm_obj
    light.parent_type = "BONE"
    light.parent_bone = "Root"
    light.location = (x, y, z - 0.20)
    light.empty_display_type = "PLAIN_AXES"
    light.empty_display_size = 0.25

    light.EDMEmptyType = "Light"
    light.EDMLightColor = (1.0, 0.78, 0.52)
    light.EDMLightBrightness = 7.5
    light.EDMLightDistance = 72.0
    light.EDMisSpot = False
    light.EDMLightPhi = math.radians(80.0)
    light.EDMLightTheta = math.radians(55.0)

bpy.context.view_layer.update()

result = bpy.ops.exportedm.edm(filepath=str(out_path), skip_collision=True, skip_render=False)
print("TPG legacy dynamic light export result:", result)
if not out_path.exists() or out_path.stat().st_size < 128:
    raise RuntimeError(f"Legacy EDM was not produced correctly: {out_path}")
print(f"TPG legacy dynamic light EDM: {out_path} ({out_path.stat().st_size} bytes), lights={len(LIGHTS)}")
