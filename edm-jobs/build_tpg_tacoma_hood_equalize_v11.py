import bpy
from collections import defaultdict

# V11 evidence-based hood closeout. V10 replaced the obvious V9 scoop-like recess with
# a fixed center lift, but a constant offset can trade a recess for a center bulge.
# This pass instead derives the center-strip target from the truck's own hood shoulders
# at the same longitudinal station. It changes ONLY FBX_Plane.001 hood vertices.
# Wheel roots/animation, registration, tuning, LOD plumbing, accessories and topper are
# intentionally untouched.
body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma hero body FBX_Plane.001")

# Group hood vertices into narrow x stations. Shoulder samples are deliberately kept
# inboard enough to stay on the hood skin and away from fender crowns.
stations = defaultdict(lambda: {"center": [], "shoulder": []})
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    if not (1.08 <= x <= 2.50 and 1.10 <= z <= 1.46):
        continue
    key = round(x / 0.04) * 0.04
    ay = abs(y)
    if ay <= 0.24:
        stations[key]["center"].append(v)
    elif 0.34 <= ay <= 0.58:
        stations[key]["shoulder"].append(v)

adjusted = 0
max_move = 0.0
for key, group in stations.items():
    center = group["center"]
    shoulder = group["shoulder"]
    if not center or len(shoulder) < 2:
        continue

    # Robust local reference: sort shoulder heights and use the middle pair/median.
    zs = sorted(v.co.z for v in shoulder)
    n = len(zs)
    target = zs[n // 2] if n % 2 else 0.5 * (zs[n // 2 - 1] + zs[n // 2])

    for v in center:
        delta = target - v.co.z
        # Ignore normal stamping differences under 2.5 mm. Correct only visible
        # scoop/bulge deviations, cap movement to 10 mm, and blend 70% for continuity.
        if abs(delta) <= 0.0025:
            continue
        move = max(-0.010, min(0.010, delta * 0.70))
        v.co.z += move
        adjusted += 1
        max_move = max(max_move, abs(move))

body.data.update()
print(f"[TPG TACOMA HOOD V11] shoulder-derived scoopless equalization adjusted={adjusted} max_move={max_move:.4f}m")
