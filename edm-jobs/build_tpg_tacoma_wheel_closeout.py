import bpy

# Final closeout calibration from the dedicated Tacoma clay QA.
# IMPORTANT: move only the existing STEER roots for wheel placement. Do not
# rebuild/reparent the wheels; arg 8 roll and arg 9 steering hierarchy must remain
# exactly as exported.
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

# Final scoopless 2016 TRD Off-Road hood cleanup. Blend the center skin toward local
# shoulder height; no Sport scoop/recess/power bulge is permitted.
body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing Tacoma hero body during hood closeout smoothing")

shoulder_samples = []
for vert in body.data.vertices:
    x, y, z = vert.co.x, vert.co.y, vert.co.z
    if 1.16 <= x <= 2.45 and 0.34 <= abs(y) <= 0.60 and 1.16 <= z <= 1.46:
        shoulder_samples.append((x, z))

hood_smooth_count = 0
for vert in body.data.vertices:
    x, y, z = vert.co.x, vert.co.y, vert.co.z
    if not (1.18 <= x <= 2.42 and abs(y) <= 0.30 and 1.16 <= z <= 1.46):
        continue
    nearby = [sz for sx, sz in shoulder_samples if abs(sx - x) <= 0.055]
    if not nearby:
        continue
    shoulder_z = max(nearby)
    crown = 0.004 * max(0.0, 1.0 - abs(y) / 0.30)
    target_z = shoulder_z - 0.004 + crown
    delta = max(-0.018, min(0.018, target_z - z))
    if abs(delta) > 0.0005:
        vert.co.z += delta * 0.85
        hood_smooth_count += 1

body.data.update()

# Release-integration cleanup. Dedicated Round-3/4 clay proved that planar generated
# fascia overlays sit visibly proud of the strongly swept FBX nose. Remove those
# experimental TPG_FINAL_* inserts after the useful cab/hood/topper sculpt has run and
# retain the source-derived front clip. This is visual-only and does not touch DCS
# registration, collision, tuning, LODs, or the wheel animation hierarchy.
removed = []
for obj in list(bpy.data.objects):
    if obj.name.startswith("TPG_FINAL_"):
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)

print(f"[TPG TACOMA HOOD CLOSEOUT] scoopless center blend adjusted {hood_smooth_count} source vertices")
print(f"[TPG TACOMA RELEASE CLEANUP] removed {len(removed)} proud experimental fascia objects")
print("[TPG TACOMA CLOSEOUT] wheel double-offset corrected; arg 8/9 preserved; source front clip retained; scoopless Off-Road hood smoothed")
