import math
import bpy
from mathutils import Vector

# FIX3 starts from the exact live-tested FIX2 blend.
# User test proves two things simultaneously:
#   1) neutral launcher hierarchy is now correct (rails start forward), and
#   2) live DCS azimuth command is mirrored: a target on the port/left side
#      drives the turret starboard/right.
#
# Replace only argument-0 azimuth animation with a smooth Euler-Z curve whose
# sign matches the DCS weapon-station command. Keep geometry, hierarchy,
# connectors, fixed +11-degree rail elevation, materials, collision and EOIR
# placement unchanged.

bpy.context.scene.frame_set(100)  # DCS argument 0 / neutral
bpy.context.view_layer.update()

PIVOTS = (
    "Launcher_Azimuth_Pivot",
    "Launcher_Azimuth_Pivot_LOD1",
    "Launcher_Azimuth_Pivot_LOD2",
    "Launcher_Azimuth_Pivot_LOD3",
    "EOIR_Azimuth_Pivot",
)

# DCS argument mapping uses frame 0=-1, 100=0, 200=+1. The live FIX2 pass
# showed +argument is the side needed for the port/left target, so +argument
# must rotate the model toward +Y (port) rather than -Y (starboard).
KEYS = (
    (0,   -180.0),
    (25,  -135.0),
    (50,   -90.0),
    (75,   -45.0),
    (100,    0.0),
    (125,   45.0),
    (150,   90.0),
    (175,  135.0),
    (200,  180.0),
)

for name in PIVOTS:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Required FIX3 yaw pivot missing: {name}")

    # Neutral transform must not move when the animation representation changes.
    bpy.context.scene.frame_set(100)
    bpy.context.view_layer.update()
    neutral_before = obj.matrix_world.copy()

    obj.animation_data_clear()
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = (0.0, 0.0, 0.0)
    action = bpy.data.actions.new(f"0_{name}_FIX3_EULER_YAW")
    obj.animation_data_create()
    obj.animation_data.action = action

    for frame, angle_deg in KEYS:
        obj.rotation_euler = (0.0, 0.0, math.radians(angle_deg))
        obj.keyframe_insert(data_path="rotation_euler", frame=frame, group="DCS Argument")

    for fcurve in action.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = "LINEAR"

    bpy.context.scene.frame_set(100)
    bpy.context.view_layer.update()
    neutral_after = obj.matrix_world.copy()
    if (neutral_after.translation - neutral_before.translation).length > 1e-5:
        raise RuntimeError(f"FIX3 neutral pivot moved unexpectedly: {name}")

# Hard QA on the actual directional connector. +argument/frame150 must rotate
# toward +Y/port; -argument/frame50 must rotate toward -Y/starboard.
aim = bpy.data.objects.get("POINT_LAUNCHER_AIM")
if aim is None:
    raise RuntimeError("POINT_LAUNCHER_AIM missing")

samples = {}
for frame in (50, 100, 150):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    loc, rot, _ = aim.matrix_world.decompose()
    x_axis = rot @ Vector((1.0, 0.0, 0.0))
    samples[frame] = (loc.copy(), x_axis.copy())
    print(
        f"FIX3_AIM frame={frame} "
        f"loc={tuple(round(v,6) for v in loc)} "
        f"x_axis={tuple(round(v,6) for v in x_axis)}"
    )

if samples[100][1].x < 0.90:
    raise RuntimeError("FIX3 neutral launcher no longer points forward")
if samples[150][1].y < 0.90:
    raise RuntimeError("FIX3 +argument does not point port/+Y")
if samples[50][1].y > -0.90:
    raise RuntimeError("FIX3 -argument does not point starboard/-Y")

# Verify both missile connectors remain on the rotating hierarchy and are still
# forward at neutral with the baked +11-degree rail pitch.
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
for name in ("POINT_R73_L", "POINT_R73_R"):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Required missile connector missing: {name}")
    _, rot, _ = obj.matrix_world.decompose()
    x_axis = rot @ Vector((1.0, 0.0, 0.0))
    if x_axis.x < 0.90:
        raise RuntimeError(f"FIX3 missile connector not forward at neutral: {name}")

print("MAGURA_FIX3_YAW_TRACKING_READY=1")
