import bpy
from collections import defaultdict

# Canonical Tacoma photo-match pass.
# IMPORTANT: This is intentionally ONE source-mesh-derived body pass from FBX_Plane.001.
# All body corrections are bounded and applied in this single canonical loop so validated
# changes do not become patch-on-patch. DCS wheel hierarchy, arg 8 wheel roll, arg 9 steering,
# gameplay tuning, collision, LOD/destroyed structure, materials, registration and the
# official ED exporter are untouched.
#
# V36, 2026-09-06:
# V35 is exporter/package green. Keep its broader flatter hood and fender shoulders, then
# continue the same front-clip correction into the upper fascia so front/front-3Q clay does
# not collapse back into a narrow pointed nose below the hood. Existing FBX vertices only;
# preserve headlamp/bumper topology and all proven DCS-side behavior.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

stats = defaultdict(int)
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # DCLB cab roof: broad, nearly level slab with a controlled outer shoulder rather than
    # the rounded crossover-like crown seen in earlier clay.
    if -0.78 <= x <= 0.60 and 1.68 <= z <= 1.88 and ay <= 0.75:
        front = max(0.0, min(1.0, (x + 0.78) / 1.38))
        edge = min(1.0, ay / 0.75)
        target_z = 1.786 - 0.003 * front - 0.010 * edge
        v.co.z += max(-0.032, min(0.014, (target_z - z) * 0.72))
        stats["roof_plane"] += 1

    # Square the outer roof shoulders so the roof side break survives clay lighting.
    if -1.12 <= x <= 0.52 and 1.68 <= z <= 1.84 and 0.55 <= ay <= 0.76:
        edge = min(1.0, max(0.0, (ay - 0.55) / 0.21))
        target_z = 1.786 - 0.013 * edge
        v.co.z += max(-0.020, min(0.010, (target_z - z) * 0.58))
        target_ay = min(0.728, max(ay, 0.654 + 0.055 * max(0.0, (z - 1.68) / 0.16)))
        v.co.y += (sign * target_ay - y) * 0.42
        stats["roof_shoulders"] += 1

    # Strong canonical roof/header station. Carry the leading header forward so the roof
    # terminates above the windshield instead of flowing into the old fastback sweep.
    if 0.18 <= x <= 0.66 and 1.67 <= z <= 1.84 and ay <= 0.74:
        fx = min(1.0, max(0.0, (x - 0.18) / 0.48))
        target_z = 1.788 - 0.008 * fx
        v.co.z += max(-0.022, min(0.010, (target_z - z) * 0.64))
        v.co.x += 0.030 * fx
        stats["header_station"] += 1

    # Stand the outer A-pillar rail materially more upright.
    if 0.48 <= x <= 1.02 and 1.48 <= z <= 1.77 and 0.49 <= ay <= 0.77:
        zf = min(1.0, max(0.0, (z - 1.48) / 0.29))
        xf = 1.0 - min(1.0, abs(x - 0.75) / 0.27)
        delta_x = 0.046 * zf * xf
        v.co.x += delta_x
        v.co.y += sign * (0.0055 * zf * xf)
        stats["upper_a_pillar"] += 1

    # Narrow the upper greenhouse while retaining the original FBX window/pillar topology.
    if -1.06 <= x <= 0.90 and 1.41 <= z <= 1.73 and 0.49 <= ay <= 0.83:
        zf = max(0.0, min(1.0, (z - 1.41) / 0.32))
        front_fade = min(1.0, max(0.0, (0.90 - x) / 0.20))
        rear_fade = min(1.0, max(0.0, (x + 1.06) / 0.20))
        edge_fade = min(front_fade, rear_fade)
        delta = 0.027 * (0.34 + 0.66 * zf) * edge_fade
        v.co.y -= sign * delta
        stats["greenhouse_tuck"] += 1

    # Beltline shoulder. Paired offsets preserve the source door-top break.
    if -1.05 <= x <= 0.92 and 0.48 <= ay <= 0.79:
        if 1.285 <= z <= 1.345:
            strength = 1.0 - min(1.0, abs(z - 1.315) / 0.030)
            v.co.y += sign * (0.0100 * strength)
            stats["beltline_lower"] += 1
        elif 1.350 <= z <= 1.405:
            strength = 1.0 - min(1.0, abs(z - 1.3775) / 0.0275)
            v.co.y -= sign * (0.0060 * strength)
            stats["beltline_upper"] += 1

    # Side glass wells are the original body skin, not inserted window objects.
    if 0.555 <= ay <= 0.800 and 1.405 <= z <= 1.705:
        window = None
        if 0.06 <= x <= 0.84:
            window = (0.06, 0.84)
        elif -0.94 <= x <= -0.15:
            window = (-0.94, -0.15)
        if window is not None:
            x0, x1 = window
            ex = min((x - x0) / 0.070, (x1 - x) / 0.070, 1.0)
            ez = min((z - 1.405) / 0.055, (1.705 - z) / 0.060, 1.0)
            ey = min((ay - 0.555) / 0.045, (0.800 - ay) / 0.045, 1.0)
            strength = max(0.0, min(ex, ez, ey))
            if strength > 0.0:
                v.co.y -= sign * (0.068 * strength)
                stats["side_window_recess"] += 1

    # Source-skin perimeter shoulder gives A/B/C pillars, roof rail and beltline a readable edge.
    if 0.535 <= ay <= 0.815:
        window = None
        if 0.06 <= x <= 0.84:
            window = (0.06, 0.84)
        elif -0.94 <= x <= -0.15:
            window = (-0.94, -0.15)
        if window is not None:
            x0, x1 = window
            band = 0.0
            if 1.345 <= z < 1.405:
                band = max(band, (z - 1.345) / 0.060)
            elif 1.705 < z <= 1.790:
                band = max(band, 1.0 - (z - 1.705) / 0.085)
            if x0 - 0.105 <= x < x0 and 1.390 <= z <= 1.730:
                band = max(band, (x - (x0 - 0.105)) / 0.105)
            elif x1 < x <= x1 + 0.105 and 1.390 <= z <= 1.730:
                band = max(band, 1.0 - (x - x1) / 0.105)
            if band > 0.0:
                v.co.y += sign * (0.016 * max(0.0, min(1.0, band)))
                stats["side_window_perimeter"] += 1

    # Windshield well remains carved from the FBX body skin.
    if 0.54 <= x <= 1.10 and 1.405 <= z <= 1.705 and ay <= 0.60:
        ex = min((x - 0.54) / 0.065, (1.10 - x) / 0.070, 1.0)
        ez = min((z - 1.405) / 0.055, (1.705 - z) / 0.060, 1.0)
        strength = max(0.0, min(ex, ez))
        if strength > 0.0:
            v.co.x -= 0.052 * strength
            stats["windshield_recess"] += 1

    # Windshield perimeter shoulder, existing body vertices only.
    if ay <= 0.62:
        band = 0.0
        if 0.455 <= x < 0.54 and 1.390 <= z <= 1.730:
            band = max(band, (x - 0.455) / 0.085)
        elif 1.10 < x <= 1.195 and 1.390 <= z <= 1.730:
            band = max(band, 1.0 - (x - 1.10) / 0.095)
        if 0.53 <= x <= 1.11:
            if 1.335 <= z < 1.405:
                band = max(band, (z - 1.335) / 0.070)
            elif 1.705 < z <= 1.800:
                band = max(band, 1.0 - (z - 1.705) / 0.095)
        if band > 0.0:
            v.co.x += 0.014 * max(0.0, min(1.0, band))
            stats["windshield_perimeter"] += 1

    # Collapse the windshield front/rear X spread for a more Tacoma-like upright stance.
    if 0.46 <= x <= 1.20 and 1.36 <= z <= 1.78 and ay <= 0.66:
        zf = max(0.0, min(1.0, (z - 1.36) / 0.42))
        center = 1.0 - min(1.0, ay / 0.66)
        if zf >= 0.44:
            upper = (zf - 0.44) / 0.56
            delta = 0.066 * upper * (0.70 + 0.30 * center)
            v.co.x += delta
            stats["windshield_upper_forward"] += 1
        else:
            lower = (0.44 - zf) / 0.44
            delta = 0.026 * lower * (0.70 + 0.30 * center)
            v.co.x -= delta
            stats["windshield_lower_rearward"] += 1

    # Distinct cowl shelf directly ahead of the upright glass.
    if 1.06 <= x <= 1.48 and 1.21 <= z <= 1.43 and ay <= 0.67:
        xf = 1.0 - min(1.0, abs(x - 1.27) / 0.21)
        yf = 1.0 - min(1.0, ay / 0.67)
        v.co.z -= 0.022 * max(0.0, xf) * (0.68 + 0.32 * yf)
        stats["cowl_break"] += 1

    # Scoopless TRD Off-Road hood plateau.
    if 1.18 <= x <= 2.34 and 1.11 <= z <= 1.37 and ay <= 0.58:
        tx = min(1.0, max(0.0, (x - 1.18) / 1.16))
        target_z = 1.307 - 0.020 * tx
        blend = 0.58 if ay <= 0.30 else 0.40
        v.co.z += max(-0.018, min(0.010, (target_z - z) * blend))
        stats["hood_plateau"] += 1

    # V35 hero-body gate: broaden and square the hood deck. In V34 front clay the hood still
    # pinches inward and rounds over like a dome. Carry the deck farther outward with only a
    # shallow lateral crown, while keeping the wheel-arch/fender skin outside this envelope.
    if 1.26 <= x <= 2.30 and 1.12 <= z <= 1.39 and 0.40 <= ay <= 0.74:
        tx = min(1.0, max(0.0, (x - 1.26) / 1.04))
        edge = min(1.0, max(0.0, (ay - 0.40) / 0.34))
        target_z = 1.304 - 0.019 * tx - 0.010 * edge
        v.co.z += max(-0.022, min(0.010, (target_z - z) * 0.62))
        target_ay = ay + 0.018 * (0.35 + 0.65 * tx) * (1.0 - 0.35 * edge)
        v.co.y = sign * min(0.790, target_ay)
        stats["v35_hood_outer_deck"] += 1

    # V35 front-fender crown: establish the distinct horizontal shoulder visible above the
    # Tacoma headlamp/fender instead of letting it merge into the hood dome.
    if 1.70 <= x <= 2.38 and 1.08 <= z <= 1.34 and 0.66 <= ay <= 0.86:
        fx = min(1.0, max(0.0, (x - 1.70) / 0.68))
        fy = 1.0 - min(1.0, abs(ay - 0.76) / 0.10)
        weight = max(0.0, fy) * (0.45 + 0.55 * fx)
        target_z = 1.286 - 0.010 * fx
        v.co.z += max(-0.016, min(0.008, (target_z - z) * 0.52 * weight))
        v.co.y += sign * (0.012 * weight)
        stats["v35_fender_crown"] += 1

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
        target_z = 1.300 - 0.014 * fx
        v.co.z += max(-0.010, min(0.006, (target_z - z) * 0.30 * weight))
        stats["front_shoulders"] += 1

    # Upper grille standup, preserving bumper/headlight source topology.
    if 2.34 <= x <= 2.54 and 1.03 <= z <= 1.24 and ay <= 0.68:
        zf = min(1.0, max(0.0, (z - 1.03) / 0.21))
        yf = 1.0 - min(1.0, ay / 0.68)
        v.co.x += 0.0065 * (0.65 + 0.35 * zf) * (0.72 + 0.28 * yf)
        stats["upper_nose"] += 1

    # V36 front-face breadth: carry the squared V35 hood/fender width down into the upper
    # fascia. This targets only the outer upper-nose/headlamp shoulder band and uses small,
    # feathered Y/X offsets so the source bumper and lamp topology remains intact.
    if 2.26 <= x <= 2.56 and 0.95 <= z <= 1.22 and 0.58 <= ay <= 0.88:
        fx = min(1.0, max(0.0, (x - 2.26) / 0.30))
        fy = 1.0 - min(1.0, abs(ay - 0.735) / 0.155)
        fz = 1.0 - min(1.0, abs(z - 1.085) / 0.135)
        weight = max(0.0, fy * fz) * (0.45 + 0.55 * fx)
        v.co.y += sign * (0.016 * weight)
        v.co.x += 0.0045 * weight
        stats["v36_upper_fascia_breadth"] += 1

    # V36 hood-to-headlamp corner: keep the hood leading edge from pinching inward where it
    # meets the outer lamp/fender shoulder, producing the broader Tacoma front-3Q silhouette.
    if 2.12 <= x <= 2.42 and 1.16 <= z <= 1.31 and 0.62 <= ay <= 0.82:
        fx = min(1.0, max(0.0, (x - 2.12) / 0.30))
        fy = 1.0 - min(1.0, abs(ay - 0.72) / 0.10)
        weight = max(0.0, fx * fy)
        v.co.y += sign * (0.010 * weight)
        v.co.z += max(-0.006, min(0.004, (1.278 - z) * 0.28 * weight))
        stats["v36_hood_lamp_corner"] += 1

    # Keep the DCLB rear cab station square without touching rear-window/pillar topology.
    if -1.20 <= x <= -1.00 and 1.47 <= z <= 1.72 and ay <= 0.74:
        target_x = -1.11 - 0.006 * min(1.0, max(0.0, (z - 1.47) / 0.25))
        v.co.x += max(-0.006, min(0.006, (target_x - x) * 0.22))
        stats["rear_cab"] += 1

body.data.update()
print("[TPG TACOMA CANONICAL PHOTO MATCH] V36 front-fascia breadth source-FBX correction complete", dict(stats))
