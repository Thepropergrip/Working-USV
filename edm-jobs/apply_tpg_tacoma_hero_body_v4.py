import bpy, os

# FBX-v3 hero-body correction pass.
# Keep the validated FBX truck, wheel animation, DCS registration/tuning, LOD plumbing
# and exporter path untouched. This pass only corrects source-transform errors on the
# imported wheel assemblies and replaces the crude rectangular camper shell generated
# by build_tpg_tacoma.py with the photo-matched Tacoma shell.

# The compact FBX payload carries the wheel mesh shapes correctly, but the four wheel
# object transforms were baked at visibly wrong centers (about x +/-3.5 m and y +/-1.4 m)
# while the source body spans only x -3.05..2.70 m and y +/-0.95 m. That is why the clay
# front/3Q QA showed wheels floating far outside the fender openings. Move only the
# existing STEER roots so the original wheel geometry plus arg 8 roll / arg 9 steering
# hierarchy stays intact. The front/rear x centers preserve the Tacoma DCLB wheelbase
# and are aligned to the FBX body's visible wheel openings; z remains source-derived.
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


# V5 silhouette pass: the user's Tacoma reference shows a low-profile ARE-style
# topper with a broad, nearly flat roof and only small radiused/chamfered shoulders.
# The prior V4 crown was too arched and made the shell read like a rounded van roof.
# Four longitudinal stations keep a subtle bed-following taper without introducing
# the cargo-box look that the original procedural shell had.
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
        # Keep the bed rail fixed while allowing only the upper shell/roof to follow
        # the tiny fore-aft crown. This preserves the straight lower body line.
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

# The actual shell reference uses a long rounded-rectangle side window with a thick
# painted perimeter. Corner-cut polygons reproduce that silhouette much better than
# V4's visibly trapezoidal panes while remaining exporter-safe, lightweight meshes.
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

# Rear hatch glass follows the same rounded-rectangle language and leaves a broad
# body-color frame like the user's shell instead of spanning almost the full hatch.
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

print("[TPG TACOMA HERO V5] Source wheel centers corrected; flattened ARE-style topper roof and photo-matched side/rear glazing")
