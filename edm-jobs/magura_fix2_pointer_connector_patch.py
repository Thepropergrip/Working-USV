import bpy
from mathutils import Vector

# FIX2 starts from the exact FIX1 blend that was live-tested in DCS.
# Root cause found in the source: animate_yaw_argument() leaves the scene at
# frame 200 (-180 deg), and the launcher meshes/connectors were parented only
# afterwards with parent_keep_world(). Their matrix_parent_inverse therefore
# captured the -180-degree parent pose. When DCS later evaluates argument 0 at
# frame 100, the entire launcher branch is offset by 180 degrees: rails/missiles
# park aft and the fire-control director never agrees with the visual/moving axis.
#
# Correct that hierarchy registration only. Do NOT alter the FIX1 arg-0 action,
# geometry, connector authored transforms/positions, fixed +11-degree rail pitch,
# EOIR animation, LOD meshes, materials, or collision.

bpy.context.scene.frame_set(100)  # DCS argument 0 / neutral
bpy.context.view_layer.update()

AZ_PIVOTS = {
    "Launcher_Azimuth_Pivot",
    "Launcher_Azimuth_Pivot_LOD1",
    "Launcher_Azimuth_Pivot_LOD2",
    "Launcher_Azimuth_Pivot_LOD3",
}
EL_PIVOTS = {
    "Launcher_Elevation_Pivot",
    "Launcher_Elevation_Pivot_LOD1",
    "Launcher_Elevation_Pivot_LOD2",
    "Launcher_Elevation_Pivot_LOD3",
}

fixed = []
for obj in list(bpy.data.objects):
    parent = obj.parent
    if parent is None:
        continue
    pname = parent.name

    # Elevation pivot objects themselves were parented before the azimuth action
    # was created, so their inverse is already correct. Everything else attached
    # to the launcher pivots was attached while the scene sat at frame 200.
    needs_fix = False
    if pname in AZ_PIVOTS and obj.name not in EL_PIVOTS:
        needs_fix = True
    elif pname in EL_PIVOTS:
        needs_fix = True

    if needs_fix:
        # matrix_basis still contains the authored world transform because the
        # original parent_keep_world() used P(frame200)^-1. Re-registering the
        # inverse at neutral makes frame100 world == authored transform W0.
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
        fixed.append(obj.name)

bpy.context.view_layer.update()

# Hard QA against the authored source positions and forward direction.
EXPECTED = {
    "POINT_R73_L": Vector((-0.50, 0.64, 2.81)),
    "POINT_R73_R": Vector((-0.50, -0.64, 2.81)),
    "POINT_LAUNCHER_AIM": Vector((0.78, 0.0, 2.83)),
}
for name, expected_loc in EXPECTED.items():
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Required MAGURA connector missing: {name}")
    loc, rot, _ = obj.matrix_world.decompose()
    x_axis = rot @ Vector((1.0, 0.0, 0.0))
    if (loc - expected_loc).length > 0.01:
        raise RuntimeError(f"Neutral connector location wrong after hierarchy fix: {name} got {tuple(loc)} expected {tuple(expected_loc)}")
    if x_axis.x < 0.90:
        raise RuntimeError(f"Neutral connector still points aft: {name} x_axis={tuple(x_axis)}")
    print(f"FIX2_NEUTRAL {name} loc={tuple(round(v,6) for v in loc)} x_axis={tuple(round(v,6) for v in x_axis)}")

front = bpy.data.objects.get("APU73_Front_Stop_L")
rear = bpy.data.objects.get("APU73_Rear_Stop_L")
if front is None or rear is None:
    raise RuntimeError("Launcher rail QA objects missing")
if front.matrix_world.translation.x <= rear.matrix_world.translation.x:
    raise RuntimeError("Launcher rail geometry is still reversed at neutral")
print(f"FIX2_RAIL_NEUTRAL front_x={front.matrix_world.translation.x:.6f} rear_x={rear.matrix_world.translation.x:.6f}")
print(f"FIX2_HIERARCHY_OBJECTS={len(fixed)}")

# Verify the connector follows the existing full-circle argument rather than
# remaining fixed. Neutral is forward; +/-1 endpoints are aft as expected.
aim = bpy.data.objects["POINT_LAUNCHER_AIM"]
for frame in (0, 100, 200):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    _, rot, _ = aim.matrix_world.decompose()
    x_axis = rot @ Vector((1.0, 0.0, 0.0))
    print(f"FIX2_AIM_FRAME frame={frame} x_axis={tuple(round(v,6) for v in x_axis)} loc={tuple(round(v,6) for v in aim.matrix_world.translation)}")

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print("MAGURA_FIX2_NEUTRAL_HIERARCHY_READY=1")
