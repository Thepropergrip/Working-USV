import bpy
from collections import defaultdict

# V29 bounded hero-body correction after clay review of V28.
# Existing FBX_Plane.001 vertices only: no new topology, objects, remesh, wheels,
# animation, gameplay, collision, registration, materials, LOD structure, or exporter changes.
# Goal: replace the long crossover-like roof/windshield/hood ramp with a more deliberate
# third-gen Tacoma cab header, upright windshield stance, and narrower upper greenhouse.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

stats = defaultdict(int)
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # Flatten the forward roof/header station so the roof does not continuously arc into
    # the windshield. Bounded to the cab roof skin and excludes topper/accessories.
    if -0.18 <= x <= 0.55 and 1.70 <= z <= 1.86 and ay <= 0.74:
        xf = max(0.0, min(1.0, (x + 0.18) / 0.73))
        target_z = 1.802 - 0.010 * xf
        v.co.z += max(-0.015, min(0.014, (target_z - z) * 0.58))
        stats["roof_header_flatten"] += 1

    # Stronger but still bounded differential windshield stance. Upper rail moves forward;
    # lower cowl edge moves rearward, producing a distinct header/windshield/cowl break.
    if 0.46 <= x <= 1.20 and 1.37 <= z <= 1.78 and ay <= 0.66:
        zf = max(0.0, min(1.0, (z - 1.37) / 0.41))
        center = 1.0 - min(1.0, ay / 0.66)
        if zf >= 0.50:
            upper = (zf - 0.50) / 0.50
            v.co.x += 0.038 * upper * (0.72 + 0.28 * center)
            stats["windshield_upper_forward"] += 1
        else:
            lower = (0.50 - zf) / 0.50
            v.co.x -= 0.024 * lower * (0.72 + 0.28 * center)
            stats["windshield_lower_rearward"] += 1

    # Pull the upper cab sides inward while leaving the lower door skin and beltline alone.
    # This reduces the inflated one-piece slab look visible in V28 side/front-3Q clay.
    if -1.06 <= x <= 0.88 and 1.43 <= z <= 1.72 and 0.50 <= ay <= 0.82:
        zf = max(0.0, min(1.0, (z - 1.43) / 0.29))
        xf_front = min(1.0, max(0.0, (0.88 - x) / 0.18))
        xf_rear = min(1.0, max(0.0, (x + 1.06) / 0.18))
        edge_fade = min(xf_front, xf_rear)
        delta = 0.026 * (0.40 + 0.60 * zf) * edge_fade
        v.co.y -= sign * delta
        stats["greenhouse_tuck"] += 1

    # Reinforce the cowl step immediately ahead of the glass without touching the fenders.
    if 1.08 <= x <= 1.48 and 1.23 <= z <= 1.42 and ay <= 0.64:
        fx = 1.0 - min(1.0, abs(x - 1.28) / 0.20)
        yf = 1.0 - min(1.0, ay / 0.64)
        v.co.z -= 0.012 * max(0.0, fx) * (0.70 + 0.30 * yf)
        stats["cowl_step"] += 1

body.data.update()
print("[TPG TACOMA V29 CAB BREAK] source-mesh hero-body correction complete", dict(stats))
