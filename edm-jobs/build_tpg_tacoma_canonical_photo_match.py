import bpy
from collections import defaultdict

# Canonical Tacoma photo-match pass.
# IMPORTANT: This is intentionally ONE source-mesh-derived body pass from FBX_Plane.001.
# All body corrections are bounded and applied in this single canonical loop so validated
# changes do not become patch-on-patch. DCS wheel hierarchy, arg 8 wheel roll, arg 9 steering,
# gameplay tuning, collision, LOD/destroyed structure, materials, registration and the
# official ED exporter are untouched.
#
# V33, 2026-09-06:
# V32's separate chained silhouette pass was retired after visual rejection. Keep the proven
# canonical-only architecture and make the next correction here: reduce the artificial
# roof/header/windshield discontinuity by flattening the forward roof station, carrying the
# header slightly FORWARD into the windshield plane, and reducing the upper-glass shove.
# Existing FBX vertices only; no new topology or DCS-system changes.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

stats = defaultdict(int)
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # V33 cab crown: flatter front-to-rear roof station with slightly stronger shoulder falloff.
    # This targets the Tacoma's broad, nearly level DCLB roof without the failed V32 extra pass.
    if -0.72 <= x <= 0.58 and 1.70 <= z <= 1.86 and ay <= 0.74:
        front = max(0.0, min(1.0, (x + 0.72) / 1.30))
        edge = min(1.0, ay / 0.74)
        target_z = 1.790 - 0.004 * front - 0.006 * edge
        v.co.z += max(-0.022, min(0.010, (target_z - z) * 0.58))
        stats["v33_roof_crown"] += 1

    # Square the outer roof shoulders so the roof does not read like a crossover dome.
    if -1.12 <= x <= 0.48 and 1.70 <= z <= 1.84 and 0.56 <= ay <= 0.74:
        edge = min(1.0, max(0.0, (ay - 0.56) / 0.18))
        target_z = 1.790 - 0.009 * edge
        v.co.z += max(-0.014, min(0.008, (target_z - z) * 0.46))
        target_ay = min(0.720, max(ay, 0.650 + 0.050 * max(0.0, (z - 1.70) / 0.14)))
        v.co.y += (sign * target_ay - y) * 0.34
        stats["roof_shoulders"] += 1

    # V33 leading header break: keep a distinct roof-front station, but move it slightly
    # forward into the upper windshield plane instead of rearward. This removes the fastback
    # kink produced by the old opposing header/glass X offsets.
    if 0.22 <= x <= 0.62 and 1.69 <= z <= 1.84 and ay <= 0.73:
        fx = min(1.0, max(0.0, (x - 0.22) / 0.40))
        target_z = 1.792 - 0.010 * fx
        v.co.z += max(-0.016, min(0.007, (target_z - z) * 0.52))
        v.co.x += 0.0100 * fx
        stats["v33_roof_header_break"] += 1

    # Stand only the OUTER upper A-pillar rail more upright. Center windshield remains for
    # the dedicated recess and stance logic below.
    if 0.50 <= x <= 1.00 and 1.50 <= z <= 1.76 and 0.50 <= ay <= 0.76:
        zf = min(1.0, max(0.0, (z - 1.50) / 0.26))
        xf = 1.0 - min(1.0, abs(x - 0.75) / 0.25)
        delta_x = 0.024 * zf * xf
        v.co.x += delta_x
        v.co.y += sign * (0.0040 * zf * xf)
        stats["upper_a_pillar"] += 1

    # Upper-greenhouse tuck: separate the glasshouse visually from the lower door skins.
    if -1.04 <= x <= 0.88 and 1.43 <= z <= 1.72 and 0.50 <= ay <= 0.82:
        zf = max(0.0, min(1.0, (z - 1.43) / 0.29))
        front_fade = min(1.0, max(0.0, (0.88 - x) / 0.18))
        rear_fade = min(1.0, max(0.0, (x + 1.04) / 0.18))
        edge_fade = min(front_fade, rear_fade)
        delta = 0.022 * (0.38 + 0.62 * zf) * edge_fade
        v.co.y -= sign * delta
        stats["greenhouse_tuck"] += 1

    # Beltline shoulder. Paired small offsets define the door-top shoulder.
    if -1.05 <= x <= 0.92 and 0.48 <= ay <= 0.79:
        if 1.285 <= z <= 1.345:
            strength = 1.0 - min(1.0, abs(z - 1.315) / 0.030)
            v.co.y += sign * (0.0080 * strength)
            stats["beltline_lower"] += 1
        elif 1.350 <= z <= 1.405:
            strength = 1.0 - min(1.0, abs(z - 1.3775) / 0.0275)
            v.co.y -= sign * (0.0045 * strength)
            stats["beltline_upper"] += 1

    # Proven source-FBX side window wells. Keep depth unchanged at 55 mm.
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

    # Source-skin glasshouse perimeter bands so pillars/rails survive smooth clay shading.
    if 0.545 <= ay <= 0.805:
        window = None
        if 0.08 <= x <= 0.82:
            window = (0.08, 0.82)
        elif -0.92 <= x <= -0.17:
            window = (-0.92, -0.17)
        if window is not None:
            x0, x1 = window
            band = 0.0
            if 1.365 <= z < 1.415:
                band = max(band, (z - 1.365) / 0.050)
            elif 1.695 < z <= 1.775:
                band = max(band, 1.0 - (z - 1.695) / 0.080)
            if x0 - 0.085 <= x < x0 and 1.405 <= z <= 1.715:
                band = max(band, (x - (x0 - 0.085)) / 0.085)
            elif x1 < x <= x1 + 0.085 and 1.405 <= z <= 1.715:
                band = max(band, 1.0 - (x - x1) / 0.085)
            if band > 0.0:
                v.co.y += sign * (0.010 * max(0.0, min(1.0, band)))
                stats["side_window_perimeter_band"] += 1

    # Proven windshield well. Keep depth unchanged at 45 mm.
    if 0.56 <= x <= 1.08 and 1.415 <= z <= 1.695 and ay <= 0.59:
        ex = min((x - 0.56) / 0.055, (1.08 - x) / 0.060, 1.0)
        ez = min((z - 1.415) / 0.045, (1.695 - z) / 0.050, 1.0)
        strength = max(0.0, min(ex, ez))
        if strength > 0.0:
            v.co.x -= 0.045 * strength
            stats["windshield_recess"] += 1

    # Source-skin windshield perimeter shoulders.
    if ay <= 0.61:
        band = 0.0
        if 0.485 <= x < 0.56 and 1.405 <= z <= 1.715:
            band = max(band, (x - 0.485) / 0.075)
        elif 1.08 < x <= 1.165 and 1.405 <= z <= 1.715:
            band = max(band, 1.0 - (x - 1.08) / 0.085)
        if 0.55 <= x <= 1.09:
            if 1.350 <= z < 1.415:
                band = max(band, (z - 1.350) / 0.065)
            elif 1.695 < z <= 1.785:
                band = max(band, 1.0 - (z - 1.695) / 0.090)
        if band > 0.0:
            v.co.x += 0.010 * max(0.0, min(1.0, band))
            stats["windshield_perimeter_band"] += 1

    # V33 differential windshield stance. Keep the lower cowl anchor, but reduce the old
    # upper-forward shove so the header and glass form one upright plane rather than a kink.
    if 0.48 <= x <= 1.18 and 1.38 <= z <= 1.76 and ay <= 0.64:
        zf = max(0.0, min(1.0, (z - 1.38) / 0.38))
        center = 1.0 - min(1.0, ay / 0.64)
        if zf >= 0.48:
            upper = (zf - 0.48) / 0.52
            delta = 0.030 * upper * (0.72 + 0.28 * center)
            v.co.x += delta
            stats["v33_windshield_upper_forward"] += 1
        else:
            lower = (0.48 - zf) / 0.48
            delta = 0.020 * lower * (0.72 + 0.28 * center)
            v.co.x -= delta
            stats["windshield_lower_rearward"] += 1

    # Stronger center cowl step immediately ahead of the glass, bounded away from fenders.
    if 1.08 <= x <= 1.46 and 1.23 <= z <= 1.42 and ay <= 0.66:
        xf = 1.0 - min(1.0, abs(x - 1.27) / 0.19)
        yf = 1.0 - min(1.0, ay / 0.66)
        v.co.z -= 0.014 * max(0.0, xf) * (0.70 + 0.30 * yf)
        stats["cowl_break"] += 1

    # Scoopless TRD Off-Road hood plateau.
    if 1.18 <= x <= 2.34 and 1.11 <= z <= 1.37 and ay <= 0.58:
        tx = min(1.0, max(0.0, (x - 1.18) / 1.16))
        target_z = 1.307 - 0.020 * tx
        blend = 0.54 if ay <= 0.30 else 0.36
        v.co.z += max(-0.016, min(0.010, (target_z - z) * blend))
        stats["hood_plateau"] += 1

    # Hood-leading break.
    if 2.10 <= x <= 2.34 and 1.18 <= z <= 1.34 and ay <= 0.62:
        fx = min(1.0, max(0.0, (x - 2.10) / 0.24))
        fy = 1.0 - min(1.0, ay / 0.62)
        weight = max(0.0, fx * (0.55 + 0.45 * fy))
        target_z = 1.292 - 0.012 * fx
        v.co.z += max(-0.012, min(0.006, (target_z - z) * 0.42 * weight))
        stats["hood_leading_break"] += 1

    # Outer hood/fender shoulder.
    if 1.48 <= x <= 2.20 and 1.12 <= z <= 1.34 and 0.56 <= ay <= 0.80:
        fx = min(1.0, max(0.0, (x - 1.48) / 0.72))
        fy = 1.0 - min(1.0, abs(ay - 0.68) / 0.12)
        weight = max(0.0, fx * fy)
        target_ay = min(0.855, ay + 0.014 * weight)
        v.co.y = sign * target_ay
        target_z = 1.300 - 0.014 * min(1.0, max(0.0, (x - 1.48) / 0.72))
        v.co.z += max(-0.010, min(0.006, (target_z - z) * 0.30 * weight))
        stats["front_shoulders"] += 1

    # Upper grille standup, preserving bumper/headlight source topology.
    if 2.34 <= x <= 2.54 and 1.03 <= z <= 1.24 and ay <= 0.68:
        zf = min(1.0, max(0.0, (z - 1.03) / 0.21))
        yf = 1.0 - min(1.0, ay / 0.68)
        v.co.x += 0.0065 * (0.65 + 0.35 * zf) * (0.72 + 0.28 * yf)
        stats["upper_nose"] += 1

    # Keep the DCLB rear cab station square without touching the rear-door window/pillar.
    if -1.20 <= x <= -1.00 and 1.47 <= z <= 1.72 and ay <= 0.74:
        target_x = -1.11 - 0.006 * min(1.0, max(0.0, (z - 1.47) / 0.25))
        v.co.x += max(-0.006, min(0.006, (target_x - x) * 0.22))
        stats["rear_cab"] += 1

body.data.update()
print("[TPG TACOMA CANONICAL PHOTO MATCH] V33 roof/header/windshield alignment complete", dict(stats))
