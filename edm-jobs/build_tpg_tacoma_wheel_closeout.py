import bpy

# Final closeout calibration from the dedicated Tacoma clay QA.
# IMPORTANT: move only the existing STEER roots for wheel placement. Do not
# rebuild/reparent the wheels; arg 8 roll and arg 9 steering hierarchy must remain
# exactly as exported.
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

# Final 2016 TRD Off-Road hood cleanup. V9's center-only downward correction could
# visually read as a shallow Sport-style scoop/recess in front and 3Q clay. The real
# Off-Road hood is scoopless, so blend only the central top skin toward the surrounding
# hood-shoulder height at the same longitudinal station. This is deliberately small,
# capped, and does not touch the grille, lamps, fenders, wheel openings, rig, tuning,
# collision, LOD structure, or exporter plumbing.
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
    # Use the local upper hood shoulder rather than an average that could include
    # underside/crease vertices. Preserve only a few millimeters of natural center crown.
    shoulder_z = max(nearby)
    crown = 0.004 * max(0.0, 1.0 - abs(y) / 0.30)
    target_z = shoulder_z - 0.004 + crown
    delta = max(-0.018, min(0.018, target_z - z))
    if abs(delta) > 0.0005:
        vert.co.z += delta * 0.85
        hood_smooth_count += 1

body.data.update()
print(f"[TPG TACOMA HOOD CLOSEOUT] scoopless center blend adjusted {hood_smooth_count} source vertices")
print("[TPG TACOMA CLOSEOUT] wheel double-offset corrected; arg 8/9 preserved; scoopless Off-Road hood surface smoothed")
