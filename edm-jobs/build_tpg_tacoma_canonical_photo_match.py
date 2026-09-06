import bpy
from collections import defaultdict

# Canonical Tacoma photo-match pass.
# IMPORTANT: This is intentionally ONE source-mesh-derived body pass from FBX_Plane.001.
# It replaces the old cumulative deformation chain. All body corrections are bounded and
# applied in this single canonical loop so validated changes do not become patch-on-patch.
# DCS wheel hierarchy, arg 8 wheel roll, arg 9 steering, gameplay tuning, collision,
# LOD/destroyed structure, materials, registration and official ED exporter are untouched.
#
# V28 consolidation, 2026-09-06:
# V27's bounded windshield/header/cowl stance correction was source-mesh-derived but had
# accidentally become a second geometry script after this pass. Fold that validated logic
# into the canonical loop and retire the chained invocation. This is an architecture cleanup,
# not a new procedural shell: existing FBX_Plane.001 vertices only, no topology/objects/remesh.

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

    # Leading roof/header break.
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

    # Beltline shoulder. Paired small offsets define the door-top shoulder while leaving
    # the window wells and actual pillar borders local and independent.
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

    # Canonicalized V27 windshield stance: differential movement makes the glass envelope
    # more upright without adding a second body pass.
    if 0.50 <= x <= 1.16 and 1.40 <= z <= 1.76 and ay <= 0.64:
        zf = max(0.0, min(1.0, (z - 1.40) / 0.36))
        center = 1.0 - min(1.0, ay / 0.64)
        if zf >= 0.48:
            upper = (zf - 0.48) / 0.52
            delta = 0.025 * upper * (0.72 + 0.28 * center)
            v.co.x += delta
            stats["windshield_upper_forward"] += 1
        else:
            lower = (0.48 - zf) / 0.48
            delta = 0.012 * lower * (0.72 + 0.28 * center)
            v.co.x -= delta
            stats["windshield_lower_rearward"] += 1

    # Canonicalized V27 roof/header station.
    if 0.28 <= x <= 0.58 and 1.70 <= z <= 1.86 and ay <= 0.74:
        xf = max(0.0, min(1.0, (x - 0.28) / 0.30))
        edge = min(1.0, ay / 0.74)
        v.co.z -= 0.008 * xf * (0.82 + 0.18 * edge)
        stats["header_station"] += 1

    # Retain the small canonical cowl break.
    if 1.12 <= x <= 1.42 and 1.29 <= z <= 1.40 and ay <= 0.76:
        fx = 1.0 - min(1.0, abs(x - 1.27) / 0.15)
        v.co.z -= 0.0035 * fx
        stats["cowl"] += 1

    # Canonicalized V27 tighter center cowl station, still bounded away from fenders/lamps.
    if 1.08 <= x <= 1.43 and 1.26 <= z <= 1.41 and ay <= 0.66:
        xf = 1.0 - min(1.0, abs(x - 1.255) / 0.175)
        yf = 1.0 - min(1.0, ay / 0.66)
        v.co.z -= 0.009 * max(0.0, xf) * (0.72 + 0.28 * yf)
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
print("[TPG TACOMA CANONICAL PHOTO MATCH] V28 single-pass consolidated source-mesh build complete", dict(stats))
