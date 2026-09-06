import bpy
from collections import defaultdict

# V16 photo-match pass: bounded front-cab / windshield / roof silhouette correction.
# Clay QA from the exporter-green V15 build still reads too soft and cab-forward/blobbed
# for a 2016 third-gen Tacoma. This pass works only on the source-derived hero body and
# deliberately avoids accessories, wheels, animation args, DCS registration/tuning,
# collision, LOD plumbing, destroyed structure, materials, and exporter configuration.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma hero body FBX_Plane.001")

stats = defaultdict(int)

for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # Stand the upper windshield/A-pillar envelope slightly more upright. The V15 clay
    # side view still has a long continuous hood-to-roof ramp. Move only the upper front
    # cab forward, fading to zero at cowl height and roof center. Max correction 16 mm.
    if 0.58 <= x <= 1.34 and 1.43 <= z <= 1.79 and 0.42 <= ay <= 0.82:
        fz = min(1.0, max(0.0, (z - 1.43) / 0.28))
        fy = 1.0 - min(1.0, abs(ay - 0.64) / 0.24)
        fx_front = min(1.0, max(0.0, (1.34 - x) / 0.24)) if x > 1.10 else 1.0
        delta = 0.016 * fz * fy * fx_front
        v.co.x += delta
        stats["upper_apillar_stand"] += 1

    # Flatten the front roof/header crown into the more deliberate Tacoma double-cab
    # profile. Keep center roof and rear roof untouched; only a narrow front header band
    # is nudged toward a nearly level target, capped at 9 mm vertical movement.
    if 0.18 <= x <= 0.88 and z >= 1.745 and ay <= 0.70:
        edge = min(1.0, ay / 0.70)
        target_z = 1.812 - 0.010 * edge
        v.co.z += max(-0.009, min(0.009, (target_z - v.co.z) * 0.48))
        stats["front_roof_header"] += 1

    # Square the roof-side shoulder just behind the A-pillar. V15 still pinches inward
    # in front 3Q clay; this gives the cab a cleaner, less egg-shaped upper section.
    if -0.05 <= x <= 0.82 and 1.60 <= z <= 1.80 and 0.50 <= ay <= 0.73:
        fz = min(1.0, max(0.0, (z - 1.60) / 0.15))
        fy = 1.0 - min(1.0, abs(ay - 0.63) / 0.13)
        delta = 0.010 * fz * fy
        v.co.y += sign * delta
        stats["front_roof_shoulder"] += 1

    # Tighten the cowl break so the hood does not visually melt into the windshield in
    # side/front-3Q clay. Only a thin upper cowl band is lowered, max 7 mm.
    if 1.08 <= x <= 1.52 and 1.28 <= z <= 1.46 and ay <= 0.78:
        fx = 1.0 - min(1.0, abs(x - 1.30) / 0.22)
        fy = 1.0 - min(1.0, ay / 0.78)
        v.co.z -= 0.007 * fx * (0.55 + 0.45 * fy)
        stats["cowl_break"] += 1

body.data.update()
print("[TPG TACOMA PHOTO MATCH V16] front cab/windshield/roof silhouette correction", dict(stats))
