import bpy
from collections import defaultdict

# V32 bounded hero-silhouette validation pass, 2026-09-06.
# Fresh V31 clay was exporter-green but still visually rejected: the forward cab roof/header
# continues to fall away too softly into the windshield, the side glasshouse recess is still
# visually weak in clay, and the camper shell reads taller/swollen at the cab junction.
#
# This pass intentionally uses EXISTING vertices only. No topology, objects, materials,
# wheel hierarchy, animation args, gameplay tuning, collision, LOD/destroyed plumbing,
# registration, packaging or exporter behavior is changed. If the clay improvement proves
# correct, these bounded values can be folded back into the single canonical body pass.

stats = defaultdict(int)
body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # Re-establish a visibly flatter DCLB roof plateau. V31 lowered the bubble crown, but the
    # front half still falls toward the windshield in side clay. Raise only that forward roof
    # field toward a near-level target, with a 35 mm hard cap and edge feathering.
    if -0.92 <= x <= 0.48 and 1.68 <= z <= 1.84 and ay <= 0.70:
        xf = max(0.0, min(1.0, (x + 0.92) / 1.40))
        edge = min(1.0, ay / 0.70)
        target_z = 1.805 - 0.005 * xf - 0.004 * edge
        delta = max(-0.010, min(0.035, (target_z - z) * 0.62))
        v.co.z += delta
        stats["v32_forward_roof_plateau"] += 1

    # Sharpen the roof/header corner instead of allowing one continuous fastback curve.
    # Upper/header vertices move modestly forward; lower windshield/cowl is deliberately left
    # alone so this rotates the visible glass stance more upright rather than shifting the cab.
    if 0.34 <= x <= 0.78 and 1.61 <= z <= 1.82 and ay <= 0.72:
        zf = max(0.0, min(1.0, (z - 1.61) / 0.21))
        xf = 1.0 - min(1.0, abs(x - 0.56) / 0.22)
        weight = max(0.0, zf * xf)
        v.co.x += 0.035 * weight
        v.co.z += 0.008 * weight
        stats["v32_header_corner"] += 1

    # Carry the same upright stance into the outer A-pillar rail without touching door skins.
    if 0.48 <= x <= 1.02 and 1.46 <= z <= 1.76 and 0.48 <= ay <= 0.77:
        zf = max(0.0, min(1.0, (z - 1.46) / 0.30))
        xf = 1.0 - min(1.0, abs(x - 0.75) / 0.27)
        weight = max(0.0, zf * xf)
        v.co.x += 0.018 * weight
        stats["v32_outer_a_pillar"] += 1

    # The proven side-window wells are still nearly disappearing in smooth clay. Add only
    # 15 mm more depth to the same bounded front/rear window interiors; pillar bands remain.
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
                v.co.y -= sign * (0.015 * strength)
                stats["v32_window_depth"] += 1

body.data.update()

# Camper-shell silhouette: retain the exporter-proven V16 object and deform existing vertices
# only. The current cap reads too tall and too full where it meets the cab. Lower just the cap
# roof field by at most 45 mm and taper only the upper front transition by at most 1.4%.
topper = bpy.data.objects.get("CAMPER_HERO_SHELL_V16")
if topper is not None and topper.type == 'MESH':
    for v in topper.data.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z

        if z >= 1.76:
            zf = max(0.0, min(1.0, (z - 1.76) / 0.20))
            v.co.z -= 0.045 * (0.45 + 0.55 * zf)
            stats["v32_topper_roof_lower"] += 1

        if -1.55 <= x <= -1.06 and z >= 1.50:
            front = 1.0 - min(1.0, max(0.0, (-1.06 - x) / 0.49))
            v.co.y *= 1.0 - 0.014 * front
            # Pull the very front upper station into a cleaner near-vertical plane.
            if z >= 1.63:
                target_x = -1.115
                v.co.x += max(-0.010, min(0.010, (target_x - x) * 0.20 * front))
            stats["v32_topper_front_transition"] += 1

    topper.data.update()
else:
    print("[TPG TACOMA V32] CAMPER_HERO_SHELL_V16 not present; body corrections still applied")

print("[TPG TACOMA V32] bounded cab/header/window/topper silhouette pass complete", dict(stats))
