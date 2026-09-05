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

# V10 closeout silhouette correction. This is intentionally the final narrow hero-body
# pass: square the cab/roof transition enough to read as a 2016 third-gen Tacoma and
# eliminate the residual scoop-like center depression in the TRD Off-Road hood.
# Wheel centers, beltline, doors, wheel openings, bed, rig, arguments, tuning, LOD
# plumbing, topper dimensions and exporter path remain untouched.
body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma hero body FBX_Plane.001")

cab_count = roof_count = windshield_count = hood_count = nose_count = 0
for vert in body.data.vertices:
    x, y, z = vert.co.x, vert.co.y, vert.co.z

    # Keep the source lower cab width. Above the beltline, taper toward the roof to get
    # the straighter Tacoma greenhouse shoulders without touching doors/fenders.
    if -0.86 <= x <= 1.08 and z >= 1.33:
        t = min(1.0, max(0.0, (z - 1.33) / 0.47))
        vert.co.y *= (1.0 - 0.070 * t)
        cab_count += 1

        # Final roof closeout: V9 clay still looked too domed/van-like. Compress only
        # the upper crown and leave the lower roof rails/A-pillars source-derived.
        if z > 1.66:
            vert.co.z = 1.66 + (z - 1.66) * 0.42
            roof_count += 1

    # Stand the upper windshield/header up more decisively. The V9 clay still rolled
    # continuously from hood into roof; a third-gen Tacoma has a clearer A-pillar/header
    # break. Move only upper-front greenhouse vertices, strongest near the roof header.
    if 0.44 <= x <= 1.12 and z >= 1.38:
        tz = min(1.0, max(0.0, (z - 1.38) / 0.38))
        tx = min(1.0, max(0.0, (x - 0.44) / 0.68))
        vert.co.x += 0.105 * tz * (0.50 + 0.50 * tx)
        windshield_count += 1

    # 2016 TRD Off-Road hood: broad and scoopless. Lower the overall source crown a
    # touch, then RAISE/blend the center strip slightly relative to V9 so it cannot read
    # as a recessed Sport-style scoop slot in front/3Q clay.
    if 1.00 <= x <= 2.58 and 1.00 <= z <= 1.43:
        tz = min(1.0, max(0.0, (z - 1.00) / 0.43))
        vert.co.y *= (1.0 - 0.028 * tz)
        vert.co.z -= 0.017 * tz
        center_blend = max(0.0, 1.0 - min(1.0, abs(y) / 0.38))
        vert.co.z += 0.006 * tz * center_blend
        hood_count += 1

    # Retain the proven 2016 third-gen upper front-clip correction. Lower bumper and
    # wheel openings remain untouched.
    if x >= 2.30 and 0.78 <= z <= 1.28:
        tx = min(1.0, max(0.0, (x - 2.30) / 0.40))
        tz = min(1.0, max(0.0, (z - 0.78) / 0.50))
        vert.co.x += (0.020 + 0.022 * tz) * tx
        vert.co.y *= (1.0 - 0.012 * tx)
        nose_count += 1

    # Preserve the hood-to-grille break from V8/V9.
    if x >= 2.12 and 1.24 <= z <= 1.46:
        tx = min(1.0, max(0.0, (x - 2.12) / 0.46))
        vert.co.x += 0.022 * tx
        vert.co.z += 0.010 * tx

body.data.update()
print(f"[TPG TACOMA HERO V10] source sculpt cab={cab_count} roof={roof_count} windshield={windshield_count} hood={hood_count} nose={nose_count}")

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

print("[TPG TACOMA HERO V10] wheel closeout calibration preserved; cab/header squared; scoopless 2016 Off-Road hood blended; V5 ARE-style topper retained")
