import bpy
from collections import defaultdict

# V17 photo-match pass: define the third-gen Tacoma double-cab glasshouse/beltline.
# V16 is exporter-green, but clay QA still reads too much like one inflated cab shell:
# the upper doors/glasshouse stay nearly flush with the lower door skins, the beltline
# lacks the Tacoma's shoulder, and the A-pillar/windshield remains visually too swept.
# This pass is intentionally source-mesh-only and bounded to the hero cab. It does not
# touch accessories, wheels, arg 8/9 animation, DCS registration/tuning, collision,
# LOD/destroyed architecture, materials, or the official ED exporter pipeline.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma hero body FBX_Plane.001")

stats = defaultdict(int)

for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # Inset the side glasshouse relative to the lower door skin. The 2016 Tacoma has a
    # visibly narrower greenhouse above the beltline; V16 clay is almost slab-flush.
    # Feather at A/B/rear-cab edges and roof/beltline so no hard artificial seam is made.
    if -0.72 <= x <= 1.22 and 1.30 <= z <= 1.69 and 0.58 <= ay <= 0.90:
        fx_front = min(1.0, max(0.0, (1.22 - x) / 0.24))
        fx_rear = min(1.0, max(0.0, (x + 0.72) / 0.24))
        fz_low = min(1.0, max(0.0, (z - 1.30) / 0.12))
        fz_high = min(1.0, max(0.0, (1.69 - z) / 0.14))
        fy = min(1.0, max(0.0, (ay - 0.58) / 0.16))
        w = fx_front * fx_rear * fz_low * fz_high * fy
        v.co.y -= sign * (0.030 * w)
        stats["glasshouse_inset"] += 1

    # Re-establish the characteristic Tacoma beltline shoulder immediately below the
    # side glasshouse. This is a small outward crease, strongest through the two doors,
    # fading before the front fender and rear cab wall. Max outward change is 14 mm.
    if -0.72 <= x <= 1.30 and 1.20 <= z <= 1.34 and 0.60 <= ay <= 0.91:
        fx_front = min(1.0, max(0.0, (1.30 - x) / 0.28))
        fx_rear = min(1.0, max(0.0, (x + 0.72) / 0.28))
        fz = 1.0 - min(1.0, abs(z - 1.275) / 0.075)
        fy = min(1.0, max(0.0, (ay - 0.60) / 0.20))
        v.co.y += sign * (0.014 * fx_front * fx_rear * fz * fy)
        stats["beltline_shoulder"] += 1

    # Make the windshield/A-pillar read decisively less swept than the V16 clay. V16's
    # 16 mm adjustment was deliberately conservative and remains visually insufficient.
    # Move only the upper A-pillar envelope forward, with a 46 mm maximum and smooth
    # fade into cowl and roof so hood/front-clip geometry remains untouched.
    if 0.62 <= x <= 1.28 and 1.46 <= z <= 1.77 and 0.46 <= ay <= 0.82:
        fz_low = min(1.0, max(0.0, (z - 1.46) / 0.18))
        fz_high = min(1.0, max(0.0, (1.77 - z) / 0.12))
        fy = 1.0 - min(1.0, abs(ay - 0.66) / 0.20)
        fx = min(1.0, max(0.0, (1.28 - x) / 0.30)) if x > 0.98 else 1.0
        v.co.x += 0.046 * fz_low * fz_high * fy * fx
        stats["apillar_upright"] += 1

    # Square the roof-side corner over the front/rear doors after the glasshouse inset.
    # The goal is the flatter, deliberate Tacoma double-cab roof section rather than the
    # rounded egg-shell shoulder still evident in V16 front 3Q clay.
    if -0.58 <= x <= 0.86 and 1.64 <= z <= 1.80 and 0.50 <= ay <= 0.75:
        fx_front = min(1.0, max(0.0, (0.86 - x) / 0.20))
        fx_rear = min(1.0, max(0.0, (x + 0.58) / 0.20))
        fz = min(1.0, max(0.0, (z - 1.64) / 0.10))
        fy = 1.0 - min(1.0, abs(ay - 0.64) / 0.14)
        v.co.y += sign * (0.016 * fx_front * fx_rear * fz * fy)
        stats["roof_side_square"] += 1

body.data.update()
print("[TPG TACOMA PHOTO MATCH V17] double-cab glasshouse/beltline silhouette refinement", dict(stats))
