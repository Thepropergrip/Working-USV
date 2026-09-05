import bpy, os
from collections import defaultdict

# Tacoma FBX-v3 canonical clean rebuild pass.
# One bounded correction from the original source-derived Tacoma mesh. No V4/V11/V12
# patch chain is resumed here. DCS wheel hierarchy/animations and gameplay tuning stay
# outside this visual pass and remain untouched.

WHEEL_TARGETS = {
    "FBX_Cylinder_STEER":      ( 1.74, -0.805),
    "FBX_Cylinder.001_STEER": (-1.83, -0.805),
    "FBX_Cylinder.002_STEER": ( 1.74,  0.805),
    "FBX_Cylinder.003_STEER": (-1.83,  0.805),
}
for name, (tx, ty) in WHEEL_TARGETS.items():
    root = bpy.data.objects.get(name)
    if root is None:
        raise RuntimeError(f"Missing source-derived Tacoma wheel animation root: {name}")
    root.location.x = tx
    root.location.y = ty

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

# Measured from the source payload in CI: source body z 0.562..1.323, roof x about
# -1.29..0.745. These bounds intentionally use the real FBX coordinate system rather
# than the obsolete procedural-model coordinates that caused V12/V13's zero-hit cab pass.
stats = defaultdict(int)
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)

    # Double-cab upper body. Keep the Tacoma roof/cab visibly square and only mildly
    # tapered. This acts on the source mesh itself, including its window/aperture shape.
    if -1.34 <= x <= 0.82 and z >= 1.105:
        tz = min(1.0, max(0.0, (z - 1.105) / 0.218))
        if ay >= 0.46:
            v.co.y *= (1.0 + 0.020 * tz)
            stats["greenhouse"] += 1
        # Push the upper roof shoulder outward, not the center crown. The source roof
        # is already numerically flat at ~1.323 m; the old problem was rounded shoulders.
        ay2 = abs(v.co.y)
        if 0.58 <= ay2 <= 0.79 and z >= 1.235:
            band = 1.0 - min(1.0, abs(ay2 - 0.69) / 0.11)
            move = 0.020 * band * min(1.0, max(0.0, (z - 1.235) / 0.088))
            v.co.y += move if v.co.y >= 0 else -move
            stats["shoulders"] += 1
        # Clamp only tiny roof crown excursions so the top reads as a Tacoma roof.
        if z >= 1.305 and ay <= 0.66:
            v.co.z = min(v.co.z, 1.3215)
            stats["roof"] += 1

    # Stand the windshield/header up from the source geometry. Front is +X. Move only
    # upper/cowl vertices; doors, rocker, fenders, wheel openings and lower A pillars stay
    # source-derived. This creates the sharper hood/cowl/windshield break in the photos.
    if 0.52 <= x <= 1.18 and 1.105 <= z <= 1.318:
        tz = min(1.0, max(0.0, (z - 1.105) / 0.213))
        tx = 1.0 - min(1.0, max(0.0, (x - 0.52) / 0.66))
        v.co.x += 0.080 * tz * (0.55 + 0.45 * tx)
        stats["windshield"] += 1

    # Scoopless 2016 TRD Off-Road hood: retain the source stamping while reducing the
    # center crown. This was already a valid source-mesh selection in the previous run.
    if 1.00 <= x <= 2.47 and 1.00 <= z <= 1.323:
        tz = min(1.0, max(0.0, (z - 1.00) / 0.323))
        v.co.y *= (1.0 - 0.012 * tz)
        v.co.z -= 0.010 * tz
        stats["hood"] += 1

    # Conservative third-gen nose correction only; no lower-front procedural rebuild.
    if x >= 2.30 and 0.78 <= z <= 1.28:
        tx = min(1.0, max(0.0, (x - 2.30) / 0.18))
        tz = min(1.0, max(0.0, (z - 0.78) / 0.50))
        v.co.x += (0.016 + 0.014 * tz) * tx
        v.co.y *= (1.0 - 0.008 * tx)
        stats["nose"] += 1

# Equalize only the hood center against shoulder heights at the same x station.
stations = defaultdict(lambda: {"center": [], "shoulder": []})
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    if not (1.08 <= x <= 2.44 and 1.07 <= z <= 1.33):
        continue
    key = round(x / 0.04) * 0.04
    ay = abs(y)
    if ay <= 0.24:
        stations[key]["center"].append(v)
    elif 0.34 <= ay <= 0.58:
        stations[key]["shoulder"].append(v)
for group in stations.values():
    if not group["center"] or len(group["shoulder"]) < 2:
        continue
    zs = sorted(v.co.z for v in group["shoulder"])
    n = len(zs)
    target = zs[n//2] if n % 2 else 0.5 * (zs[n//2-1] + zs[n//2])
    for v in group["center"]:
        delta = target - v.co.z
        if abs(delta) > 0.0025:
            v.co.z += max(-0.010, min(0.010, delta * 0.65))
            stats["hood_equalized"] += 1
body.data.update()

# Replace the base box camper with a low-profile ARE-style shell matched to the user's
# real-truck reference. The source cab roof is ~1.323 m; the topper roof is therefore
# ~1.34 m, not the erroneous 1.77 m of the rejected candidate.
REMOVE_PREFIXES = (
    "CAMPER_BODY", "CAMPER_ROOF", "CAMPER_SIDE_GLASS_", "CAMPER_REAR_GLASS",
    "CAMPER_HERO_SHELL_",
)
for obj in list(bpy.data.objects):
    if obj.name.startswith(REMOVE_PREFIXES):
        bpy.data.objects.remove(obj, do_unlink=True)

destroyed = os.environ.get("TPG_TACOMA_DESTROYED", "0") == "1"
paint = bpy.data.materials.get("TPG_TACOMA_Burnt" if destroyed else "TPG_TACOMA_Quicksand_4T8")
glass = bpy.data.materials.get("TPG_TACOMA_TintedGlass")
if paint is None or glass is None:
    raise RuntimeError("Tacoma clean-rebuild materials are missing")

def make_mesh(name, verts, faces, material, smooth=True, bevel=0.0):
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces); me.update()
    obj = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(obj)
    me.materials.append(material)
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((co.x * 0.18 + co.y * 0.13) % 1.0,
                                  (co.z * 0.32 + co.y * 0.17) % 1.0)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    if bevel > 0.0:
        mod = obj.modifiers.new("hero_edge_soften", "BEVEL"); mod.width = bevel; mod.segments = 3
        bpy.context.view_layer.objects.active = obj
        try: bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception: pass
    return obj

stations_shell = [
    (-1.08, 0.990, -0.002), (-1.48, 1.000, 0.002),
    (-2.16, 1.000, 0.002), (-2.68, 0.990, -0.004),
]
# Cross-section ordered driver lower -> roof -> passenger lower. Nearly vertical shell
# sides and a gently radiused roof match the reference much better than the tall dome.
profile = [
    (-0.865, 1.000), (-0.865, 1.185), (-0.842, 1.285), (-0.790, 1.325),
    (-0.690, 1.342), (0.690, 1.342), (0.790, 1.325), (0.842, 1.285),
    (0.865, 1.185), (0.865, 1.000),
]
verts = []
for x, width_scale, roof_add in stations_shell:
    for y, z in profile:
        t = max(0.0, min(1.0, (z - 1.18) / 0.17))
        verts.append((x, y * width_scale, z + roof_add * t))
n = len(profile)
faces = []
for s in range(len(stations_shell) - 1):
    a, b = s*n, (s+1)*n
    for i in range(n-1): faces.append((a+i, a+i+1, b+i+1, b+i))
faces.append(tuple(range(n-1, -1, -1)))
rear0 = (len(stations_shell)-1)*n
faces.append(tuple(rear0+i for i in range(n)))
make_mesh("CAMPER_HERO_SHELL_V13", verts, faces, paint, smooth=True, bevel=0.014)

for side in (-1, 1):
    y = side * 0.852
    win = [
        (-2.48,y,1.055),(-2.48,y,1.220),(-2.40,y,1.292),
        (-1.34,y,1.292),(-1.25,y,1.255),(-1.22,y,1.055)
    ]
    face = [tuple(range(len(win)))] if side > 0 else [tuple(range(len(win)-1,-1,-1))]
    make_mesh(f"CAMPER_SIDE_GLASS_HERO_{side}", win, face, glass, smooth=False)
rear_x = -2.687
rear = [
    (rear_x,-0.665,1.050),(rear_x,0.665,1.050),(rear_x,0.665,1.220),
    (rear_x,0.600,1.292),(rear_x,-0.600,1.292),(rear_x,-0.665,1.220)
]
make_mesh("CAMPER_REAR_GLASS_HERO", rear, [tuple(range(len(rear)))], glass, smooth=False)

# Base custom accessories were authored around the rejected 1.7-1.9 m procedural cap.
# Re-seat the two roof platforms and hood ditch lights to the real source-body heights.
for obj in bpy.data.objects:
    if obj.name.startswith("RACK_RAIL_") or obj.name.startswith("RACK_BAR_"):
        obj.location.z -= 0.455
    elif obj.name.startswith("BLACK_OAK_") or obj.name.startswith("DITCH_BRACKET_"):
        obj.location.z -= 0.205

print("[TPG TACOMA CLEAN V13] canonical FBX source rebuild complete", dict(stats))
