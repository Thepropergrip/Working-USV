import bpy, os

# FBX-v3 hero-body correction pass.
# Keep the validated FBX truck, wheel animation, DCS registration/tuning, LOD plumbing
# and exporter path untouched. This pass corrects source-transform errors on the
# imported wheel assemblies, applies a conservative source-mesh Tacoma front/cab
# silhouette sculpt, and replaces the crude rectangular camper shell generated
# by build_tpg_tacoma.py with the photo-matched Tacoma shell.

# The compact FBX payload carries the wheel mesh shapes correctly, but the four wheel
# object transforms were baked at visibly wrong centers (about x +/-3.5 m and y +/-1.4 m)
# while the source body spans only x -3.05..2.70 m and y +/-0.95 m. Move only the
# existing STEER roots so the original wheel geometry plus arg 8 roll / arg 9 steering
# hierarchy stays intact.
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
    old = root.location.copy()
    root.location.x = tx
    root.location.y = ty
    print(f"[TPG TACOMA FBX WHEEL CENTER] {name}: ({old.x:.3f},{old.y:.3f},{old.z:.3f}) -> ({tx:.3f},{ty:.3f},{old.z:.3f})")

# V7 front/cab silhouette correction. This REPLACES the V6 sculpt; it is not an
# additional patch layered on top. Every build starts from the compact original-FBX
# body payload, then this single source-vertex pass is applied once. Clay V6 proved the
# wheel centers substantially corrected but the greenhouse still read too rounded and
# van-like in side/3Q views. V7 therefore works on the actual source body only: it
# narrows the roof more decisively, flattens the crown, and stands the windshield upper
# edge slightly more upright while preserving the beltline, doors, wheel openings, bed,
# rig, arguments, tuning, LOD plumbing and exporter path.
body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma hero body FBX_Plane.001")

cab_count = roof_count = windshield_count = hood_count = nose_count = 0
for vert in body.data.vertices:
    x, y, z = vert.co.x, vert.co.y, vert.co.z

    # Narrow only above the beltline. Strength ramps toward the roof so lower door and
    # fender widths remain source-derived. A 7.5% maximum roof narrowing gives the cab
    # the visibly straighter Tacoma greenhouse shoulders missing in V6.
    if -0.86 <= x <= 1.08 and z >= 1.33:
        t = min(1.0, max(0.0, (z - 1.33) / 0.47))
        vert.co.y *= (1.0 - 0.075 * t)
        cab_count += 1

        # Flatten only the highest crown. Do not impose a procedural roof shape; retain
        # each source vertex and compress excess crown height smoothly toward ~1.80 m.
        if z > 1.72:
            vert.co.z = 1.72 + (z - 1.72) * 0.62
            roof_count += 1

    # The V6 side silhouette still had too much windshield rake. Shift only upper-front
    # greenhouse vertices forward, strongest at the roof header, to stand the screen up
    # without touching the hood/cowl or creating a new mesh.
    if 0.48 <= x <= 1.10 and z >= 1.40:
        tz = min(1.0, max(0.0, (z - 1.40) / 0.40))
        tx = min(1.0, max(0.0, (x - 0.48) / 0.62))
        vert.co.x += 0.055 * tz * (0.55 + 0.45 * tx)
        windshield_count += 1

    # Keep the hood shoulder broad but less domed. This is intentionally smaller than
    # the cab correction because the V6 front clip was already close in clay QA.
    if 1.00 <= x <= 2.58 and 1.00 <= z <= 1.43:
        tz = min(1.0, max(0.0, (z - 1.00) / 0.43))
        vert.co.y *= (1.0 - 0.030 * tz)
        center = max(0.0, 1.0 - min(1.0, abs(y) / 0.90))
        vert.co.z -= 0.016 * tz * (1.0 - 0.35 * center)
        hood_count += 1

    # Preserve the conservative squared nose correction from V6.
    if x >= 2.38 and 0.62 <= z <= 1.24:
        tx = min(1.0, max(0.0, (x - 2.38) / 0.32))
        vert.co.x += 0.018 * tx
        vert.co.y *= (1.0 - 0.018 * tx)
        nose_count += 1

body.data.update()
print(f"[TPG TACOMA HERO V7] source sculpt cab={cab_count} roof={roof_count} windshield={windshield_count} hood={hood_count} nose={nose_count}")

REMOVE_PREFIXES = (
    "CAMPER_BODY",
    "CAMPER_ROOF",
    "CAMPER_SIDE_GLASS_",
    "CAMPER_REAR_GLASS",
    "CAMPER_HERO_SHELL_",
)

for obj in list(bpy.data.objects):
    if obj.name.startswith(REMOVE_PREFIXES):
        bpy.data.objects.remove(obj, do_unlink=True)

destroyed = os.environ.get("TPG_TACOMA_DESTROYED", "0") == "1"
paint = bpy.data.materials.get("TPG_TACOMA_Burnt" if destroyed else "TPG_TACOMA_Quicksand_4T8")
glass = bpy.data.materials.get("TPG_TACOMA_TintedGlass")
if paint is None or glass is None:
    raise RuntimeError("Tacoma hero-body materials are missing")


def make_mesh(name, verts, faces, material, smooth=True, bevel=0.0):
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    me.materials.append(material)

    # Match the UV contract used by build_tpg_tacoma.py. ED's default material
    # exporter requires a UV layer for the base/AORMS texture blocks even when the
    # source textures are effectively flat-color swatches.
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((co.x * 0.18 + co.y * 0.13) % 1.0,
                                  (co.z * 0.32 + co.y * 0.17) % 1.0)

    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
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


# V5 topper silhouette retained: low-profile ARE-style shell with broad, nearly flat
# roof and small radiused shoulders. Four stations give only a subtle bed-following taper.
stations = [
    (-1.02, 0.985, -0.004),
    (-1.48, 1.000,  0.004),
    (-2.16, 1.000,  0.004),
    (-2.68, 0.988, -0.006),
]
profile = [
    (-0.870, 1.155),
    (-0.862, 1.500),
    (-0.835, 1.660),
    (-0.760, 1.730),
    (-0.610, 1.770),
    ( 0.610, 1.770),
    ( 0.760, 1.730),
    ( 0.835, 1.660),
    ( 0.862, 1.500),
    ( 0.870, 1.155),
]
verts = []
for x, width_scale, roof_add in stations:
    for y, z in profile:
        t = max(0.0, min(1.0, (z - 1.50) / 0.27))
        verts.append((x, y * width_scale, z + roof_add * t))

n = len(profile)
faces = []
for s in range(len(stations) - 1):
    a = s * n
    b = (s + 1) * n
    for i in range(n - 1):
        faces.append((a + i, a + i + 1, b + i + 1, b + i))
faces.append(tuple(range(n - 1, -1, -1)))
rear0 = (len(stations) - 1) * n
faces.append(tuple(rear0 + i for i in range(n)))
make_mesh("CAMPER_HERO_SHELL_V5", verts, faces, paint, smooth=True, bevel=0.018)

for side in (-1, 1):
    y = side * 0.852
    win = [
        (-2.47, y, 1.305),
        (-2.47, y, 1.555),
        (-2.40, y, 1.625),
        (-1.33, y, 1.625),
        (-1.25, y, 1.585),
        (-1.22, y, 1.305),
    ]
    face = [tuple(range(len(win)))] if side > 0 else [tuple(range(len(win) - 1, -1, -1))]
    make_mesh(f"CAMPER_SIDE_GLASS_HERO_{side}", win, face, glass, smooth=False)

rear_x = -2.687
rear = [
    (rear_x, -0.650, 1.300),
    (rear_x,  0.650, 1.300),
    (rear_x,  0.650, 1.555),
    (rear_x,  0.585, 1.625),
    (rear_x, -0.585, 1.625),
    (rear_x, -0.650, 1.555),
]
make_mesh("CAMPER_REAR_GLASS_HERO", rear, [tuple(range(len(rear)))], glass, smooth=False)

print("[TPG TACOMA HERO V7] source wheel centers corrected; source greenhouse/roof/windshield silhouette refined; V5 ARE-style topper retained")
