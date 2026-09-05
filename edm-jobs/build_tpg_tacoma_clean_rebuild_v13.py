import bpy, os
from collections import defaultdict

# Tacoma FBX-v3 canonical clean rebuild pass.
# This replaces the accumulated hero/V11/V12 body-patch chain. It starts from the
# original FBX-derived body produced by build_tpg_tacoma.py, then performs ONE bounded
# source-mesh reconstruction guided by the user's real 2016 Tacoma reference photos.
# DCS mechanics are intentionally untouched: proven wheel hierarchy, arg 8 wheel roll,
# arg 9 steering, unit tuning, LOD/destroyed plumbing, exporter path and packaging.

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

stats = defaultdict(int)

# Canonical source-body reconstruction. All coordinates below are bounded to the
# original FBX body and avoid doors, wheel openings, lower fenders and the DCS rig.
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)

    # Third-gen Tacoma greenhouse: keep the upper cab noticeably more vertical and
    # square than the V12 candidate. The old chain narrowed the crown and then tried
    # to push shoulders back out; here the shape is solved once from the source mesh.
    if -0.86 <= x <= 1.05 and z >= 1.34:
        tz = min(1.0, max(0.0, (z - 1.34) / 0.34))
        # Only a mild roof taper from the lower cab instead of the old 7% pinch.
        v.co.y *= (1.0 - 0.025 * tz)
        stats["greenhouse"] += 1

        # Square the upper side shoulders directly from the source mesh.
        ay2 = abs(v.co.y)
        if 0.44 <= ay2 <= 0.78 and z >= 1.48:
            band = 1.0 - min(1.0, abs(ay2 - 0.61) / 0.17)
            move = 0.028 * min(1.0, max(0.0, (z - 1.48) / 0.20)) * band
            v.co.y += move if v.co.y >= 0 else -move
            stats["shoulders"] += 1

        # Flatten the roof crown decisively. This is the hard visual correction for
        # the V12 van-like/domed silhouette while preserving the roof edge vertices.
        if z > 1.64 and abs(v.co.y) <= 0.60:
            v.co.z = 1.64 + (z - 1.64) * 0.24
            stats["roof"] += 1

    # Sharpen the hood/cowl/A-pillar break by standing the upper windshield/header
    # farther forward. Lower pillar bases and doors stay source-derived.
    if 0.42 <= x <= 1.12 and z >= 1.36:
        tz = min(1.0, max(0.0, (z - 1.36) / 0.36))
        tx = min(1.0, max(0.0, (x - 0.42) / 0.70))
        v.co.x += 0.150 * tz * (0.55 + 0.45 * tx)
        stats["windshield"] += 1

    # Broad scoopless TRD Off-Road hood. Reduce crown slightly while preserving the
    # source stamping; center-strip equalization is solved station-by-station below.
    if 1.00 <= x <= 2.58 and 1.00 <= z <= 1.43:
        tz = min(1.0, max(0.0, (z - 1.00) / 0.43))
        v.co.y *= (1.0 - 0.020 * tz)
        v.co.z -= 0.015 * tz
        stats["hood"] += 1

    # Retain the proven third-gen upper front-clip correction only.
    if x >= 2.30 and 0.78 <= z <= 1.28:
        tx = min(1.0, max(0.0, (x - 2.30) / 0.40))
        tz = min(1.0, max(0.0, (z - 0.78) / 0.50))
        v.co.x += (0.020 + 0.022 * tz) * tx
        v.co.y *= (1.0 - 0.012 * tx)
        stats["nose"] += 1

    if x >= 2.12 and 1.24 <= z <= 1.46:
        tx = min(1.0, max(0.0, (x - 2.12) / 0.46))
        v.co.x += 0.022 * tx
        v.co.z += 0.010 * tx

# Equalize only the hood center from the hood's own shoulder heights at each x station.
stations = defaultdict(lambda: {"center": [], "shoulder": []})
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    if not (1.08 <= x <= 2.50 and 1.08 <= z <= 1.46):
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
            v.co.z += max(-0.012, min(0.012, delta * 0.75))
            stats["hood_equalized"] += 1

body.data.update()

# Replace the base generated camper with the validated photo-matched shell, without
# touching any FBX body or DCS mechanics.
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
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    me.materials.append(material)
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((co.x * 0.18 + co.y * 0.13) % 1.0,
                                  (co.z * 0.32 + co.y * 0.17) % 1.0)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if bevel > 0.0:
        mod = obj.modifiers.new("hero_edge_soften", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception:
            pass
    return obj

stations_shell = [
    (-1.02, 0.985, -0.004), (-1.48, 1.000, 0.004),
    (-2.16, 1.000, 0.004), (-2.68, 0.988, -0.006),
]
profile = [
    (-0.870, 1.155), (-0.862, 1.500), (-0.835, 1.660), (-0.760, 1.730),
    (-0.610, 1.770), (0.610, 1.770), (0.760, 1.730), (0.835, 1.660),
    (0.862, 1.500), (0.870, 1.155),
]
verts = []
for x, width_scale, roof_add in stations_shell:
    for y, z in profile:
        t = max(0.0, min(1.0, (z - 1.50) / 0.27))
        verts.append((x, y * width_scale, z + roof_add * t))
n = len(profile)
faces = []
for s in range(len(stations_shell) - 1):
    a, b = s*n, (s+1)*n
    for i in range(n-1):
        faces.append((a+i, a+i+1, b+i+1, b+i))
faces.append(tuple(range(n-1, -1, -1)))
rear0 = (len(stations_shell)-1)*n
faces.append(tuple(rear0+i for i in range(n)))
make_mesh("CAMPER_HERO_SHELL_V13", verts, faces, paint, smooth=True, bevel=0.018)

for side in (-1, 1):
    y = side * 0.852
    win = [(-2.47,y,1.305),(-2.47,y,1.555),(-2.40,y,1.625),(-1.33,y,1.625),(-1.25,y,1.585),(-1.22,y,1.305)]
    face = [tuple(range(len(win)))] if side > 0 else [tuple(range(len(win)-1,-1,-1))]
    make_mesh(f"CAMPER_SIDE_GLASS_HERO_{side}", win, face, glass, smooth=False)
rear_x = -2.687
rear = [(rear_x,-0.650,1.300),(rear_x,0.650,1.300),(rear_x,0.650,1.555),(rear_x,0.585,1.625),(rear_x,-0.585,1.625),(rear_x,-0.650,1.555)]
make_mesh("CAMPER_REAR_GLASS_HERO", rear, [tuple(range(len(rear)))], glass, smooth=False)

print("[TPG TACOMA CLEAN V13] canonical FBX source rebuild complete", dict(stats))
