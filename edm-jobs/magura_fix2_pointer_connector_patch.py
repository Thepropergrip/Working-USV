import math
import bpy
from mathutils import Matrix, Quaternion

# FIX2 is intentionally narrow. It starts from the exact FIX1 blend that the
# user live-tested in DCS and changes only the three directional connectors.
# The argument-0 launcher/EOIR animation, geometry, +11 degree fixed rail pitch,
# LODs, materials, collision, and all other model data remain untouched.

bpy.context.scene.frame_set(100)  # DCS argument 0 / neutral
bpy.context.view_layer.update()

NAMES = ("POINT_R73_L", "POINT_R73_R", "POINT_LAUNCHER_AIM")

for name in NAMES:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Required MAGURA connector missing: {name}")

    before = obj.matrix_world.copy()
    loc, rot, scale = before.decompose()
    x_before = rot @ __import__('mathutils').Vector((1.0, 0.0, 0.0))

    # The live FIX1 screenshot proves the attached AIM-9X models are 180 degrees
    # aft at neutral. Rotate only the connector orientation 180 degrees around
    # boat/world vertical at the connector origin; do not move the connector.
    flip = Quaternion((0.0, 0.0, 1.0), math.pi)
    rot2 = flip @ rot
    obj.matrix_world = Matrix.LocRotScale(loc, rot2, scale)
    bpy.context.view_layer.update()

    after = obj.matrix_world.copy()
    loc2, rot_after, scale2 = after.decompose()
    x_after = rot_after @ __import__('mathutils').Vector((1.0, 0.0, 0.0))

    if (loc2 - loc).length > 1e-5:
        raise RuntimeError(f"Connector moved unexpectedly: {name}")
    print(f"FIX2_CONNECTOR {name} loc={tuple(round(v,6) for v in loc2)} "
          f"x_before={tuple(round(v,6) for v in x_before)} "
          f"x_after={tuple(round(v,6) for v in x_after)}")

# Return scene to neutral before save/export.
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print("MAGURA_FIX2_POINTER_CONNECTOR_READY=1")
