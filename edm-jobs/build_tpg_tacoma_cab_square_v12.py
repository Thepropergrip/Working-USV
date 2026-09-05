import bpy

# V12 narrow hero-body closeout: square the upper cab/roof shoulders without touching
# doors, beltline, wheel arches, hood, topper, accessories, or any DCS mechanics.
# V10/V11 already address front clip and scoopless hood. The remaining recurring clay
# weakness is a too-rounded/van-like greenhouse. This pass uses small bounded moves on
# FBX_Plane.001 only so the 2016 third-gen Tacoma cab reads flatter across the crown and
# more vertical through the upper side shoulders.
body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma hero body FBX_Plane.001")

shoulder_count = crown_count = 0
max_y_move = max_z_move = 0.0

for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z

    # Upper cab only. Keep A/B/C pillar bases and door glass beltline untouched.
    if -0.78 <= x <= 0.98 and 1.56 <= z <= 1.76:
        ay = abs(y)

        # Gently push the upper side shoulders outward, strongest in the 0.48-0.72 m
        # band where a rounded source greenhouse tends to roll inward toward the roof.
        # Cap at ~14 mm total movement so this cannot distort the lower cab width.
        if 0.46 <= ay <= 0.76:
            tz = min(1.0, max(0.0, (z - 1.56) / 0.20))
            side_band = 1.0 - min(1.0, abs(ay - 0.61) / 0.15)
            move = 0.014 * tz * side_band
            v.co.y += move if y >= 0.0 else -move
            shoulder_count += 1
            max_y_move = max(max_y_move, move)

        # Flatten only the central roof crown. Preserve edge rails/shoulders and use a
        # small compression toward 1.69 m to create the Tacoma's broad, flatter roof.
        if ay <= 0.44 and z > 1.69:
            old_z = v.co.z
            v.co.z = 1.69 + (v.co.z - 1.69) * 0.72
            crown_count += 1
            max_z_move = max(max_z_move, old_z - v.co.z)

body.data.update()
print(
    f"[TPG TACOMA CAB V12] shoulders={shoulder_count} crown={crown_count} "
    f"max_y_move={max_y_move:.4f}m max_z_move={max_z_move:.4f}m"
)
