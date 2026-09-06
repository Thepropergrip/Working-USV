import bpy
from collections import defaultdict

# V15 photo-match pass: bounded double-cab rear silhouette / topper transition refinement.
# The 2016 DCLB reference has a comparatively square rear-cab shoulder and a clean,
# nearly vertical cab-to-cap break. Previous passes improved the roof/front clip but
# left the rear upper cab reading too soft in side/rear-3Q clay views.
# Do not touch wheels, animation args, registration/tuning, materials, exporter,
# collision, LOD plumbing or destroyed-state structure.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma hero body FBX_Plane.001")

stats = defaultdict(int)

for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # Square the upper rear-cab side shoulder without moving the beltline or doors.
    # Maximum lateral change is 12 mm and fades out toward roof center and C-pillar edges.
    if -1.18 <= x <= -0.62 and 1.43 <= z <= 1.77 and 0.46 <= ay <= 0.72:
        fx_rear = min(1.0, max(0.0, (x + 1.18) / 0.16))
        fx_front = min(1.0, max(0.0, (-0.62 - x) / 0.16))
        fz = min(1.0, max(0.0, (z - 1.43) / 0.20))
        fy = 1.0 - min(1.0, abs(ay - 0.61) / 0.15)
        delta = 0.012 * min(fx_rear, fx_front) * fz * fy
        v.co.y += sign * delta
        stats["rear_cab_shoulder"] += 1

    # Make the upper rear cab wall read as a cleaner DCLB station in side view.
    # This is intentionally a small X correction only in the glass/header-height band.
    if -1.24 <= x <= -0.96 and 1.40 <= z <= 1.76 and ay <= 0.79:
        tz = min(1.0, max(0.0, (z - 1.40) / 0.36))
        target_x = -1.115 - 0.010 * tz
        v.co.x += max(-0.010, min(0.010, (target_x - v.co.x) * 0.28))
        stats["rear_cab_station"] += 1

    # Keep the rear roof edge broad and nearly level so it meets the ARE-style topper
    # as one deliberate silhouette rather than a rounded drop at the cab back.
    if -1.16 <= x <= -0.82 and z >= 1.755 and ay <= 0.66:
        edge = min(1.0, ay / 0.66)
        target_z = 1.803 - 0.009 * edge
        v.co.z += max(-0.006, min(0.006, (target_z - v.co.z) * 0.55))
        stats["rear_roof_edge"] += 1

body.data.update()

# Refine only the front transition of the generated topper shell. Keep the long-bed
# length, rear station and overall roof height unchanged. A tiny front-width taper
# reduces the swollen cap-at-cab junction visible in rear/front 3Q clay.
topper = bpy.data.objects.get("CAMPER_HERO_SHELL_V16")
if topper is not None and topper.type == 'MESH':
    for v in topper.data.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z
        if -1.50 <= x <= -1.08 and z >= 1.52:
            fx = min(1.0, max(0.0, (-1.08 - x) / -0.42))
            # strongest at the front station, zero by x=-1.50
            front = 1.0 - min(1.0, max(0.0, (-1.08 - x) / 0.42))
            v.co.y *= 1.0 - 0.008 * front
            stats["topper_front_taper"] += 1
    topper.data.update()

print("[TPG TACOMA PHOTO MATCH V15] rear double-cab/topper silhouette refinement", dict(stats))
