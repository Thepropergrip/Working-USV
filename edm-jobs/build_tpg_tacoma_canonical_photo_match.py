import bpy
from collections import defaultdict

# Canonical Tacoma photo-match pass.
# IMPORTANT: This is intentionally ONE source-mesh-derived body pass from FBX_Plane.001.
# It replaces the old V13->V17 cumulative deformation chain. All body corrections use
# bounded/absolute target envelopes so they do not compound across releases.
# DCS wheel hierarchy, arg 8 wheel roll, arg 9 steering, gameplay tuning, collision,
# LOD/destroyed structure, materials, registration and official ED exporter are untouched.
#
# Visual-QA correction, 2026-09-06:
# The previous canonical pass still altered nearly the entire greenhouse and windshield
# with broad coordinate bands. Clay QA showed those bands smoothing away the source FBX's
# pillar/window/door-top definition and producing a generic featureless cab. Preserve the
# original FBX greenhouse/A-B pillar/window topology here. Only bounded roof-shoulder,
# cowl/hood, fender-shoulder, upper-nose and rear-cab station corrections remain.
#
# Exporter safety: this stage stays source-mesh-only. The exporter-proven generated topper
# is retained until any replacement topper has independently passed the ED EDM exporter.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

stats = defaultdict(int)
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # Keep the source roof centerline and pillar/header geometry. Only square the outer
    # roof shoulders slightly so the cab does not read as a rounded crossover roof.
    if -1.12 <= x <= 0.48 and 1.72 <= z <= 1.84 and 0.56 <= ay <= 0.74:
        edge = min(1.0, max(0.0, (ay - 0.56) / 0.18))
        target_z = 1.812 - 0.010 * edge
        v.co.z += max(-0.010, min(0.010, (target_z - z) * 0.40))
        target_ay = min(0.725, max(ay, 0.655 + 0.050 * max(0.0, (z - 1.72) / 0.12)))
        v.co.y += (sign * target_ay - y) * 0.30
        stats["roof_shoulders"] += 1

    # IMPORTANT: no canonical greenhouse narrowing and no canonical windshield rake.
    # Those broad bands erased source FBX window/pillar character in the clay gate.

    # Retain only a very small cowl break. The source A-pillar/windshield stays untouched.
    if 1.12 <= x <= 1.42 and 1.29 <= z <= 1.40 and ay <= 0.76:
        fx = 1.0 - min(1.0, abs(x - 1.27) / 0.15)
        v.co.z -= 0.0035 * fx
        stats["cowl"] += 1

    # Scoopless TRD Off-Road hood: flatten only the center/inner hood, not lamp/fender
    # geometry. Reduced from the prior pass to preserve source stamping and front character.
    if 1.18 <= x <= 2.34 and 1.12 <= z <= 1.36 and ay <= 0.58:
        tx = min(1.0, max(0.0, (x - 1.18) / 1.16))
        target_z = 1.315 - 0.024 * tx
        blend = 0.42 if ay <= 0.26 else 0.24
        v.co.z += max(-0.010, min(0.010, (target_z - z) * blend))
        stats["hood"] += 1

    # Mildly square the outer hood/fender shoulder while leaving wheel arches/headlamp
    # corners source-derived. This is intentionally a small bounded correction.
    if 1.58 <= x <= 2.22 and 1.13 <= z <= 1.34 and 0.56 <= ay <= 0.82:
        fx = min(1.0, max(0.0, (x - 1.58) / 0.48))
        fy = 1.0 - min(1.0, abs(ay - 0.69) / 0.13)
        target_ay = min(0.86, ay + 0.009 * fx * fy)
        v.co.y = sign * target_ay
        stats["front_shoulders"] += 1

    # Preserve the source bumper/headlight surfaces. Only a tiny upper grille-band standup.
    if x >= 2.38 and 1.00 <= z <= 1.22 and ay <= 0.82:
        v.co.x += 0.0030 * (0.65 + 0.35 * min(1.0, max(0.0, (z - 1.00) / 0.22)))
        stats["upper_nose"] += 1

    # Keep the DCLB rear cab station square without touching the rear-door window/pillar.
    if -1.20 <= x <= -1.00 and 1.47 <= z <= 1.72 and ay <= 0.74:
        target_x = -1.11 - 0.006 * min(1.0, max(0.0, (z - 1.47) / 0.25))
        v.co.x += max(-0.006, min(0.006, (target_x - x) * 0.22))
        stats["rear_cab"] += 1

body.data.update()
print("[TPG TACOMA CANONICAL PHOTO MATCH] source greenhouse/pillars preserved; bounded body pass complete", dict(stats))
