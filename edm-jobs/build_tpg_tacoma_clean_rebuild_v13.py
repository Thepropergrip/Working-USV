import bpy, os
from collections import defaultdict

# Tacoma FBX-v3 canonical clean rebuild pass.
# Round-1 geometry correction: preserve the real source FBX cab/greenhouse. The source
# mesh measured in CI reaches z=1.831 m; the prior V13 pass incorrectly treated ~1.323 m
# as cab-roof height and crushed the greenhouse by roughly half a meter.
# DCS wheel hierarchy/animations and gameplay tuning remain outside this visual pass.

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

# Preserve the source FBX cab, A/B/C pillars, windshield and roof. Only perform bounded
# hood/nose cleanup in zones that are safely forward of the greenhouse.
stats = defaultdict(int)
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z

    # Scoopless 2016 TRD Off-Road hood. Keep this correction conservative and below the
    # windshield zone; do not touch the actual greenhouse.
    if 1.00 <= x <= 2.47 and 1.00 <= z <= 1.34:
        tz = min(1.0, max(0.0, (z - 1.00) / 0.34))
        v.co.y *= (1.0 - 0.010 * tz)
        v.co.z -= 0.008 * tz
        stats["hood"] += 1

    # Conservative third-gen nose correction only.
    if x >= 2.30 and 0.78 <= z <= 1.28:
        tx = min(1.0, max(0.0, (x - 2.30) / 0.18))
        tz = min(1.0, max(0.0, (z - 0.78) / 0.50))
        v.co.x += (0.014 + 0.012 * tz) * tx
        v.co.y *= (1.0 - 0.006 * tx)
        stats["nose"] += 1

# Equalize only the hood center against shoulder heights at the same x station.
stations = defaultdict(lambda: {"center": [], "shoulder": []})
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    if not (1.08 <= x <= 2.44 and 1.07 <= z <= 1.34):
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
            v.co.z += max(-0.008, min(0.008, delta * 0.55))
            stats["hood_equalized"] += 1
body.data.update()

# Replace the base camper with a low-profile ARE-style shell matched to the user's real
# truck. The actual source cab roof is ~1.831 m, so the topper must sit essentially flush
# with it, not down at 1.34 m.
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

# Long-bed camper: lower edge follows bed rail near 1.00 m and roof is nearly level with
# the 1.831 m cab roof, with only a slight crown.
stations_shell = [
    (-1.08, 0.990, 0.000), (-1.48, 1.000, 0.004),
    (-2.16, 1.000, 0.004), (-2.68, 0.990, -0.002),
]
profile = [
    (-0.865, 1.000), (-0.865, 1.420), (-0.850, 1.650), (-0.815, 1.775),
    (-0.735, 1.825), (-0.640, 1.842), (0.640, 1.842), (0.735, 1.825),
    (0.815, 1.775), (0.850, 1.650), (0.865, 1.420), (0.865, 1.000),
]
verts = []
for x, width_scale, roof_add in stations_shell:
    for y, z in profile:
        t = max(0.0, min(1.0, (z - 1.60) / 0.25))
        verts.append((x, y * width_scale, z + roof_add * t))
n = len(profile)
faces = []
for s in range(len(stations_shell) - 1):
    a, b = s*n, (s+1)*n
    for i in range(n-1): faces.append((a+i, a+i+1, b+i+1, b+i))
faces.append(tuple(range(n-1, -1, -1)))
rear0 = (len(stations_shell)-1)*n
faces.append(tuple(rear0+i for i in range(n)))
make_mesh("CAMPER_HERO_SHELL_V14", verts, faces, paint, smooth=True, bevel=0.014)

for side in (-1, 1):
    y = side * 0.852
    win = [
        (-2.48,y,1.275),(-2.48,y,1.625),(-2.40,y,1.755),
        (-1.34,y,1.755),(-1.25,y,1.705),(-1.22,y,1.275)
    ]
    face = [tuple(range(len(win)))] if side > 0 else [tuple(range(len(win)-1,-1,-1))]
    make_mesh(f"CAMPER_SIDE_GLASS_HERO_{side}", win, face, glass, smooth=False)
rear_x = -2.687
rear = [
    (rear_x,-0.665,1.250),(rear_x,0.665,1.250),(rear_x,0.665,1.625),
    (rear_x,0.600,1.755),(rear_x,-0.600,1.755),(rear_x,-0.665,1.625)
]
make_mesh("CAMPER_REAR_GLASS_HERO", rear, [tuple(range(len(rear)))], glass, smooth=False)

# Do not apply the previous bogus -0.455 m / -0.205 m lowering. Those accessories were
# already authored around the real ~1.8 m truck roof envelope.

print("[TPG TACOMA ROUND1] source cab preserved; camper restored to true roof height", dict(stats))
