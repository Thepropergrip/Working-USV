import bpy

# Final wheel-center calibration from the dedicated V9 neutral QA OBJ.
# IMPORTANT: move only the existing STEER roots. Do not rebuild/reparent the wheels;
# arg 8 roll and arg 9 steering hierarchy must remain exactly as exported.
#
# V9 QA measured wheel mesh centers at approximately:
#   front: x=+3.540, rear: x=-3.601
#   left:  y=-1.5135, right: y=+1.523
# against the intended source-derived Tacoma centers:
#   front x=+1.740, rear x=-1.830, y=+/-0.805.
# The FBX wheel meshes already carry most of their placement in child transforms, so
# the STEER roots must stay near the origin rather than duplicating that translation.
ROOT_CALIBRATION = {
    "FBX_Cylinder_STEER":      (-0.0600, -0.0965),
    "FBX_Cylinder.001_STEER": (-0.0590, -0.0965),
    "FBX_Cylinder.002_STEER": (-0.0600,  0.0870),
    "FBX_Cylinder.003_STEER": (-0.0590,  0.0870),
}

for name, (x, y) in ROOT_CALIBRATION.items():
    root = bpy.data.objects.get(name)
    if root is None:
        raise RuntimeError(f"Missing Tacoma STEER root during closeout calibration: {name}")
    before = root.location.copy()
    root.location.x = x
    root.location.y = y
    print(f"[TPG TACOMA WHEEL CLOSEOUT] {name}: ({before.x:.4f},{before.y:.4f},{before.z:.4f}) -> ({x:.4f},{y:.4f},{before.z:.4f})")

print("[TPG TACOMA WHEEL CLOSEOUT] corrected FBX child-transform double offset; arg 8/9 hierarchy preserved")
