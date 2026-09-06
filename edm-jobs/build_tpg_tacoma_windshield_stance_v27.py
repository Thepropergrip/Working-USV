import bpy
from collections import defaultdict

# V27 hero-body correction derived from the V26 clay gate.
# The V26 export is technically green but the side/front-3Q clay still shows an overlong,
# continuous roof-to-hood ramp. This pass changes only existing FBX_Plane.001 vertices and
# is intentionally bounded to the windshield/header/cowl envelope. No new topology, no
# wheel hierarchy changes, no gameplay changes, no collision/LOD/exporter/package changes.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

stats = defaultdict(int)
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)

    # Stand the windshield envelope more upright without flattening the glass field.
    # Upper windshield/header vertices move forward while the lower cowl edge moves only
    # slightly rearward. The differential is deliberately capped at 37 mm total.
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

    # Make the roof/header junction a visible station rather than a soft continuous arc.
    # This is a millimeter-scale Z break across the front roof band only.
    if 0.28 <= x <= 0.58 and 1.70 <= z <= 1.86 and ay <= 0.74:
        xf = max(0.0, min(1.0, (x - 0.28) / 0.30))
        edge = min(1.0, ay / 0.74)
        v.co.z -= 0.008 * xf * (0.82 + 0.18 * edge)
        stats["header_station"] += 1

    # Tighten the cowl break so the hood stops visually flowing into the windshield.
    # Keep it inside the center cowl and below the windshield; fenders/lamp corners remain
    # source-derived and untouched.
    if 1.08 <= x <= 1.43 and 1.26 <= z <= 1.41 and ay <= 0.66:
        xf = 1.0 - min(1.0, abs(x - 1.255) / 0.175)
        yf = 1.0 - min(1.0, ay / 0.66)
        v.co.z -= 0.009 * max(0.0, xf) * (0.72 + 0.28 * yf)
        stats["cowl_break"] += 1

body.data.update()
print("[TPG TACOMA V27] windshield stance/header correction complete", dict(stats))
