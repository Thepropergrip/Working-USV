import math
import bpy
from mathutils import Quaternion


def patch_yaw(obj_name):
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        raise RuntimeError(f"Required MAGURA yaw pivot missing: {obj_name}")

    # Replace only argument-0 yaw animation. Geometry, parenting, connectors,
    # fixed +11 degree launcher pitch, EO/IR elevation, materials and LODs stay intact.
    obj.animation_data_clear()
    obj.rotation_mode = "QUATERNION"
    action = bpy.data.actions.new(f"0_{obj.name}_QUAT_FIX")
    obj.animation_data_create()
    obj.animation_data.action = action

    # DCS EDM frame convention: 100 = argument 0 / neutral.  Full-circle
    # rotations use 90-degree intermediate keys so the exporter never has to
    # infer a 180-degree Euler path.
    for frame, angle_deg in ((0, 180.0), (50, 90.0), (100, 0.0), (150, -90.0), (200, -180.0)):
        obj.rotation_quaternion = Quaternion((0.0, 0.0, 1.0), math.radians(angle_deg))
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, group="DCS Argument")

    for fcurve in action.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = "LINEAR"


for name in (
    "Launcher_Azimuth_Pivot",
    "Launcher_Azimuth_Pivot_LOD1",
    "Launcher_Azimuth_Pivot_LOD2",
    "Launcher_Azimuth_Pivot_LOD3",
    "EOIR_Azimuth_Pivot",
):
    patch_yaw(name)

bpy.context.scene.frame_set(100)
print("MAGURA_QUATERNION_YAW_FIX_READY=1")
