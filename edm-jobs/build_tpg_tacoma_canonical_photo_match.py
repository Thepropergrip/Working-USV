import bpy
from collections import defaultdict

# Canonical Tacoma photo-match pass.
# IMPORTANT: This is intentionally ONE source-mesh-derived body pass from FBX_Plane.001.
# It replaces the old V13->V17 cumulative deformation chain. All body corrections use
# bounded/absolute target envelopes so they do not compound across releases.
# DCS wheel hierarchy, arg 8 wheel roll, arg 9 steering, gameplay tuning, collision,
# LOD/destroyed structure, materials, registration and official ED exporter are untouched.
#
# V21 clay-gate correction, 2026-09-06:
# V20 proved that the source FBX window/windshield selections are valid (62 side-window
# and 69 windshield vertices were edited), but the 30/26 mm wells disappeared visually
# under the source smoothing in side/front-3Q clay QA. Keep the same original-FBX topology,
# pillar/header/beltline keep-outs and single-pass strategy, but make those wells deeper
# and their feather bands tighter so the glasshouse reads structurally at DCS viewing
# distance. No procedural replacement body panels are added.
#
# Exporter safety: source-mesh vertices only. The exporter-proven generated topper remains.

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

    # Leading roof/header break retained from V18.
    if 0.30 <= x <= 0.56 and 1.73 <= z <= 1.86 and ay <= 0.73:
        fx = min(1.0, max(0.0, (x - 0.30) / 0.26))
        target_z = 1.812 - 0.006 * fx
        v.co.z += max(-0.008, min(0.010, (target_z - z) * 0.36))
        v.co.x -= 0.0045 * fx
        stats["roof_header_break"] += 1

    # Stand only the OUTER upper A-pillar rail slightly more upright. The center windshield
    # field is left for the dedicated recess below.
    if 0.52 <= x <= 0.98 and 1.52 <= z <= 1.76 and 0.50 <= ay <= 0.76:
        zf = min(1.0, max(0.0, (z - 1.52) / 0.24))
        xf = 1.0 - min(1.0, abs(x - 0.75) / 0.23)
        delta_x = 0.018 * zf * xf
        v.co.x += delta_x
        v.co.y += sign * (0.0045 * zf * xf)
        stats["upper_a_pillar"] += 1

    # Beltline shoulder retained. Paired small offsets define the door-top shoulder while
    # leaving the window wells and actual pillar borders local and independent.
    if -1.05 <= x <= 0.92 and 0.48 <= ay <= 0.79:
        if 1.285 <= z <= 1.345:
            strength = 1.0 - min(1.0, abs(z - 1.315) / 0.030)
            v.co.y += sign * (0.0080 * strength)
            stats["beltline_lower"] += 1
        elif 1.350 <= z <= 1.405:
            strength = 1.0 - min(1.0, abs(z - 1.3775) / 0.0275)
            v.co.y -= sign * (0.0045 * strength)
            stats["beltline_upper"] += 1

    # V21 side glass relief: retain the same two original-FBX window fields and the
    # preserved B-pillar, but deepen the interior to 55 mm and tighten the feather to
    # leave a crisp geometric perimeter that survives clay smoothing. This is deformation
    # of the source body surface itself, not a generated window/body overlay.
    if 0.555 <= ay <= 0.795 and 1.415 <= z <= 1.695:
        window = None
        if 0.08 <= x <= 0.82:
            window = (0.08, 0.82)
        elif -0.92 <= x <= -0.17:
            window = (-0.92, -0.17)
        if window is not None:
            x0, x1 = window
            ex = min((x - x0) / 0.060, (x1 - x) / 0.060, 1.0)
            ez = min((z - 1.415) / 0.045, (1.695 - z) / 0.050, 1.0)
            ey = min((ay - 0.555) / 0.040, (0.795 - ay) / 0.040, 1.0)
            strength = max(0.0, min(ex, ez, ey))
            if strength > 0.0:
                v.co.y -= sign * (0.055 * strength)
                stats["side_window_recess"] += 1

    # V21 windshield relief: same central source-FBX field and untouched A-pillars/header/
    # cowl perimeter, now 45 mm rearward with a tighter feather so the windshield plane
    # and its frame are visible in front and front-3Q clay without changing the front clip.
    if 0.56 <= x <= 1.08 and 1.415 <= z <= 1.695 and ay <= 0.59:
        ex = min((x - 0.56) / 0.055, (1.08 - x) / 0.060, 1.0)
        ez = min((z - 1.415) / 0.045, (1.695 - z) / 0.050, 1.0)
        strength = max(0.0, min(ex, ez))
        if strength > 0.0:
            v.co.x -= 0.045 * strength
            stats["windshield_recess"] += 1

    # Retain only a very small cowl break.
    if 1.12 <= x <= 1.42 and 1.29 <= z <= 1.40 and ay <= 0.76:
        fx = 1.0 - min(1.0, abs(x - 1.27) / 0.15)
        v.co.z -= 0.0035 * fx
        stats["cowl"] += 1

    # Scoopless TRD Off-Road hood plateau. Flatten the inner hood while keeping lamp,
    # grille and wheel-arch corners source-derived.
    if 1.18 <= x <= 2.34 and 1.11 <= z <= 1.37 and ay <= 0.58:
        tx = min(1.0, max(0.0, (x - 1.18) / 1.16))
        target_z = 1.307 - 0.020 * tx
        blend = 0.54 if ay <= 0.30 else 0.36
        v.co.z += max(-0.016, min(0.010, (target_z - z) * blend))
        stats["hood_plateau"] += 1

    # Define the outer hood/fender shoulder as a narrow band without touching the wheel
    # arch or headlamp corner topology.
    if 1.48 <= x <= 2.20 and 1.12 <= z <= 1.34 and 0.56 <= ay <= 0.80:
        fx = min(1.0, max(0.0, (x - 1.48) / 0.72))
        fy = 1.0 - min(1.0, abs(ay - 0.68) / 0.12)
        weight = max(0.0, fx * fy)
        target_ay = min(0.855, ay + 0.014 * weight)
        v.co.y = sign * target_ay
        target_z = 1.300 - 0.014 * min(1.0, max(0.0, (x - 1.48) / 0.72))
        v.co.z += max(-0.010, min(0.006, (target_z - z) * 0.30 * weight))
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
print("[TPG TACOMA CANONICAL PHOTO MATCH] V21 sharper source-glasshouse relief complete", dict(stats))
