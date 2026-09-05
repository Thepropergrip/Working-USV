import bpy
from collections import defaultdict

# V14 photo-match pass: bounded source-mesh front-clip refinement only.
# Purpose: make the 2016 third-gen Tacoma read less rounded/soft in clay by squaring
# the hood/fender shoulders and upper nose envelope without adding any applique meshes.
# Do NOT touch wheels, steering/roll hierarchy, DCS registration/tuning, collision,
# LOD structure, destroyed structure, materials, or exporter plumbing.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma hero body FBX_Plane.001")

stats = defaultdict(int)

for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # Third-gen Tacoma hood shoulders are broad and relatively planar. The source
    # FBX/previous sculpt still pinches inward near the front corners in clay. Expand
    # only the upper fender/hood shoulder by a maximum of ~18 mm, strongest around the
    # outer hood edge and fading to zero at the centerline, wheel arch and A-pillar.
    if 1.50 <= x <= 2.50 and 1.10 <= z <= 1.36 and 0.48 <= ay <= 0.88:
        fx = min(1.0, max(0.0, (x - 1.50) / 0.65))
        # fade again at the very nose so the bumper/lamp opening stays source-derived
        nose_fade = min(1.0, max(0.0, (2.50 - x) / 0.18)) if x > 2.32 else 1.0
        fy = 1.0 - min(1.0, abs(ay - 0.70) / 0.22)
        dz = min(1.0, max(0.0, (z - 1.10) / 0.18))
        delta = 0.018 * fx * nose_fade * fy * (0.55 + 0.45 * dz)
        v.co.y += sign * delta
        stats["hood_fender_shoulder"] += 1

    # Stand the upper front face a few millimeters more upright at the lamp/grille
    # band. This is deliberately tiny and vertex-only; the proud generated fascia
    # overlays remain removed by the existing release closeout.
    if x >= 2.38 and 0.96 <= z <= 1.25 and ay <= 0.91:
        tz = min(1.0, max(0.0, (z - 0.96) / 0.29))
        edge = min(1.0, ay / 0.91)
        v.co.x += 0.006 * (0.55 + 0.45 * tz) * (1.0 - 0.20 * edge)
        stats["upper_nose_stand"] += 1

    # Preserve a crisp hood-to-fender shoulder in front 3Q without changing the hood
    # center height. This pulls only the shoulder band toward the local broad hood plane.
    if 1.72 <= x <= 2.38 and 1.19 <= z <= 1.36 and 0.52 <= ay <= 0.78:
        target_z = 1.305 - 0.020 * min(1.0, max(0.0, (x - 1.72) / 0.66))
        v.co.z += (target_z - v.co.z) * 0.16
        stats["hood_shoulder_plane"] += 1

body.data.update()

print("[TPG TACOMA PHOTO MATCH V14] bounded source front-clip shoulder/nose refinement", dict(stats))
