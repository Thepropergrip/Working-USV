import bpy
from collections import defaultdict

# Canonical Tacoma photo-match pass.
# IMPORTANT: This is intentionally ONE source-mesh-derived body pass from FBX_Plane.001.
# It replaces the old V13->V17 cumulative deformation chain. All body corrections use
# bounded/absolute target envelopes so they do not compound across releases.
# DCS wheel hierarchy, arg 8 wheel roll, arg 9 steering, gameplay tuning, collision,
# LOD/destroyed structure, materials, registration and official ED exporter are untouched.
#
# V26 clay-gate correction, 2026-09-06:
# V25 broadened the side-window perimeter bands so the sparse FBX topology can actually
# carry a visible pillar/rail normal break while preserving the proven 55 mm side wells.
# Apply the same evidence-based correction to the windshield: retain the proven 45 mm well
# exactly unchanged, but replace its narrow V23 <=50 mm frame test with broader feathered
# source-skin shoulders around the A-pillar/header/cowl perimeter. No new geometry, no
# windshield object, no deeper recess, and no front-clip movement outside that perimeter.
#
# Exporter safety remains strict: existing source FBX vertices only, bounded millimeter-scale
# deformation, no new topology/objects, no remesh, and no changes to wheel animation,
# registration, gameplay tuning, collision, LOD/destroyed structure, packaging or exporter.

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

    # Proven V21 source-FBX side window wells. Keep depth unchanged at 55 mm.
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

    # V25 source-skin glasshouse perimeter bands. The V24 edge test only found two source
    # vertices, so define wider bands immediately around the established wells. These are
    # shallow outward shoulders, not separate frames: they simply make the A/B/C pillars,
    # roof rail and beltline survive smooth clay shading on the sparse FBX topology.
    if 0.545 <= ay <= 0.805:
        window = None
        if 0.08 <= x <= 0.82:
            window = (0.08, 0.82)
        elif -0.92 <= x <= -0.17:
            window = (-0.92, -0.17)
        if window is not None:
            x0, x1 = window
            band = 0.0

            # Lower and upper rails: 75-80 mm bands centered just outside the well.
            if 1.365 <= z < 1.415:
                band = max(band, (z - 1.365) / 0.050)
            elif 1.695 < z <= 1.775:
                band = max(band, 1.0 - (z - 1.695) / 0.080)

            # Front/rear pillar shoulders: wider than V24 so real source vertices are hit.
            if x0 - 0.085 <= x < x0 and 1.405 <= z <= 1.715:
                band = max(band, (x - (x0 - 0.085)) / 0.085)
            elif x1 < x <= x1 + 0.085 and 1.405 <= z <= 1.715:
                band = max(band, 1.0 - (x - x1) / 0.085)

            if band > 0.0:
                # Cap at 10 mm. Enough for a clay normal break, far below the 55 mm well.
                v.co.y += sign * (0.010 * max(0.0, min(1.0, band)))
                stats["side_window_perimeter_band"] += 1

    # Proven V21 windshield well. Keep depth unchanged at 45 mm.
    if 0.56 <= x <= 1.08 and 1.415 <= z <= 1.695 and ay <= 0.59:
        ex = min((x - 0.56) / 0.055, (1.08 - x) / 0.060, 1.0)
        ez = min((z - 1.415) / 0.045, (1.695 - z) / 0.050, 1.0)
        strength = max(0.0, min(ex, ez))
        if strength > 0.0:
            v.co.x -= 0.045 * strength
            stats["windshield_recess"] += 1

    # V26 source-skin windshield perimeter shoulders. The old V23 <=50 mm edge test used
    # the same sparse-topology assumption that failed on the side glass. Use broader bands
    # just outside the established well so real source vertices can define the A-pillars,
    # header and cowl break in front/front-3Q clay without changing the well itself.
    if ay <= 0.61:
        band = 0.0

        # Rear/header and forward/cowl shoulders in X, immediately outside the well.
        if 0.485 <= x < 0.56 and 1.405 <= z <= 1.715:
            band = max(band, (x - 0.485) / 0.075)
        elif 1.08 < x <= 1.165 and 1.405 <= z <= 1.715:
            band = max(band, 1.0 - (x - 1.08) / 0.085)

        # Lower and upper windshield rails in Z, bounded to the windshield span.
        if 0.55 <= x <= 1.09:
            if 1.350 <= z < 1.415:
                band = max(band, (z - 1.350) / 0.065)
            elif 1.695 < z <= 1.785:
                band = max(band, 1.0 - (z - 1.695) / 0.090)

        if band > 0.0:
            # Up to 10 mm forward normal break; no topology or gross silhouette movement.
            v.co.x += 0.010 * max(0.0, min(1.0, band))
            stats["windshield_perimeter_band"] += 1

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

    # V24 hood-leading break: flatten only the final 240 mm of the upper hood and create a
    # modest downward break into the fascia. This is deliberately inside the hood field and
    # avoids headlamp corners, bumper skin and wheel-arch topology.
    if 2.10 <= x <= 2.34 and 1.18 <= z <= 1.34 and ay <= 0.62:
        fx = min(1.0, max(0.0, (x - 2.10) / 0.24))
        fy = 1.0 - min(1.0, ay / 0.62)
        weight = max(0.0, fx * (0.55 + 0.45 * fy))
        target_z = 1.292 - 0.012 * fx
        v.co.z += max(-0.012, min(0.006, (target_z - z) * 0.42 * weight))
        stats["hood_leading_break"] += 1

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

    # V24 upper grille standup. Keep the bumper/headlight surfaces source-derived and only
    # bring the central upper fascia forward a few additional millimeters so the nose reads
    # more upright beneath the new hood-leading break.
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

print("[TPG TACOMA CANONICAL PHOTO MATCH] V26 broad windshield perimeter pass complete", dict(stats))
