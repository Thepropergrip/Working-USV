import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

# True visual-only HiRes patch. The input is the exact FIX3 blend whose launcher
# geometry/yaw/connectors were live-proven. FIX5 night capability is Lua-only, so
# this blend is also the correct geometry baseline for the proven-night unit.
#
# HARD RULE: no connector, pivot, animation, collision, bounding box, weapon or
# sensor-functional transform may change. This script adds/softens visible mesh,
# closes the bow trim gaps, upgrades exposed launcher detail, and binds unique
# high-resolution texture names only.

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
TEXDIR = ROOT / "hires-generated" / "textures"
REPORT = ROOT / "hires-generated" / "visual-qa.json"
TEXDIR.mkdir(parents=True, exist_ok=True)

INTACT_LOD0 = "MAGURA_LOD_0_90"
INTACT_LOD1 = "MAGURA_LOD_1_250"
PITCH = math.radians(11.0)

PROTECTED = (
    "POINT_R73_L",
    "POINT_R73_R",
    "POINT_LAUNCHER_AIM",
    "CENTER_LAUNCHER",
    "Launcher_Azimuth_Pivot",
    "Launcher_Elevation_Pivot",
    "EOIR_Azimuth_Pivot",
    "EOIR_Elevation_Pivot",
)
SAMPLE_FRAMES = (50, 100, 150)


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        raise RuntimeError(f"Required collection missing: {name}")
    return col


def material(name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        raise RuntimeError(f"Required material missing: {name}")
    return mat


def parent_keep_world(obj, parent):
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    obj.matrix_world = world
    bpy.context.view_layer.update()


def matrix_max_delta(a, b):
    return max(abs(a[r][c] - b[r][c]) for r in range(4) for c in range(4))


def protected_snapshot():
    snap = {}
    for frame in SAMPLE_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name in PROTECTED:
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise RuntimeError(f"Protected object missing before HiRes patch: {name}")
            snap[(frame, name)] = obj.matrix_world.copy()
    bpy.context.scene.frame_set(100)
    bpy.context.view_layer.update()
    return snap


def count_triangles(colnames):
    total = 0
    for colname in colnames:
        col = bpy.data.collections.get(colname)
        if not col:
            continue
        for obj in col.all_objects:
            if obj.type != "MESH":
                continue
            for poly in obj.data.polygons:
                total += max(0, len(poly.vertices) - 2)
    return total


def set_mat(obj, mat_name):
    obj.data.materials.clear()
    obj.data.materials.append(material(mat_name))


def apply_bevel(obj, width=0.008, segments=3, angle=0.55):
    if obj.type != "MESH":
        return
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new(name="HiRes_Edge_Soften", type="BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = angle
    mod.harden_normals = True
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    finally:
        obj.select_set(False)


def add_box(name, loc, dims, mat_name, colname=INTACT_LOD0, rotation=(0.0, 0.0, 0.0), bevel=0.01, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # Move from temporary Scene Collection into the intended EDM LOD collection.
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection(colname).objects.link(obj)
    set_mat(obj, mat_name)
    if bevel > 0:
        apply_bevel(obj, bevel, 3)
    if parent is not None:
        parent_keep_world(obj, parent)
    return obj


def add_cyl(name, loc, radius, depth, mat_name, colname=INTACT_LOD0, rotation=(0.0, 0.0, 0.0), vertices=32, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection(colname).objects.link(obj)
    set_mat(obj, mat_name)
    if parent is not None:
        parent_keep_world(obj, parent)
    return obj


def add_torus(name, loc, major, minor, mat_name, colname=INTACT_LOD0, rotation=(0.0, 0.0, 0.0), parent=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=12, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection(colname).objects.link(obj)
    set_mat(obj, mat_name)
    if parent is not None:
        parent_keep_world(obj, parent)
    return obj


def add_wedge(name, verts, faces, mat_name, colname=INTACT_LOD0, bevel=0.012):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection(colname).objects.link(obj)
    set_mat(obj, mat_name)
    for poly in mesh.polygons:
        poly.use_smooth = True
    if bevel > 0:
        apply_bevel(obj, bevel, 3, 0.30)
    return obj


def add_curve(name, points, radius, mat_name, colname=INTACT_LOD0, parent=None):
    curve = bpy.data.curves.new(name + "_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 4
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    collection(colname).objects.link(obj)
    curve.materials.append(material(mat_name))
    if parent is not None:
        parent_keep_world(obj, parent)
    return obj


def load_hires_image(filename, non_color=False):
    path = TEXDIR / filename
    if not path.exists():
        raise RuntimeError(f"HiRes texture missing: {path}")
    existing = bpy.data.images.get(Path(filename).stem)
    if existing:
        img = existing
        img.filepath = str(path)
    else:
        img = bpy.data.images.load(str(path), check_existing=False)
    img.name = Path(filename).stem
    img.filepath = str(path)
    if non_color:
        try:
            img.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
    return img


def find_shader(mat, socket_name):
    if not mat.use_nodes or not mat.node_tree:
        return None
    for node in mat.node_tree.nodes:
        if hasattr(node, "inputs") and socket_name in node.inputs:
            return node
    return None


def bind(mat_name, socket_name, filename, non_color=False):
    mat = material(mat_name)
    shader = find_shader(mat, socket_name)
    if shader is None:
        print(f"HIRES_BIND_SKIP material={mat_name} socket={socket_name}")
        return False
    img = load_hires_image(filename, non_color)
    node = mat.node_tree.nodes.new(type="ShaderNodeTexImage")
    node.name = f"HiRes_{Path(filename).stem}_{socket_name}"
    node.image = img
    node.interpolation = "Linear"
    mat.node_tree.links.new(node.outputs["Color"], shader.inputs[socket_name])
    return True


def tune_default(mat_name, base=None, roughmet=None):
    mat = material(mat_name)
    shader = find_shader(mat, "Base Color") or find_shader(mat, "RoughMet (Non-Color)")
    if shader is None:
        return
    if base is not None and "Base Color" in shader.inputs:
        shader.inputs["Base Color"].default_value = base
    if roughmet is not None and "RoughMet (Non-Color)" in shader.inputs:
        shader.inputs["RoughMet (Non-Color)"].default_value = roughmet


before = protected_snapshot()
tri_before = count_triangles((INTACT_LOD0, INTACT_LOD1))
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

# ---------------------------------------------------------------------------
# 1. BOW CLOSEOUT: close the visible jagged openings where the side fender/trim
#    terminates at the bow nose block. Two tapered skin closeouts sit beneath two
#    continuous rubber bridges so there is no daylight hole from oblique angles.
# ---------------------------------------------------------------------------
for side_name, sign in (("Port", 1.0), ("Starboard", -1.0)):
    outer_rear = sign * 0.285
    inner_rear = sign * 0.225
    outer_front = sign * 0.165
    inner_front = sign * 0.115
    verts = [
        (3.265, outer_rear, 0.790),
        (3.260, outer_rear, 0.650),
        (3.535, outer_front, 0.840),
        (3.525, outer_front, 0.690),
        (3.265, inner_rear, 0.775),
        (3.260, inner_rear, 0.655),
        (3.535, inner_front, 0.825),
        (3.525, inner_front, 0.700),
    ]
    faces = [
        (0, 2, 3, 1), (4, 5, 7, 6), (0, 4, 6, 2),
        (1, 3, 7, 5), (0, 1, 5, 4), (2, 6, 7, 3),
    ]
    add_wedge(f"HiRes_Bow_Skin_Closeout_{side_name}", verts, faces, "MAGURA_W6_Hull", INTACT_LOD0, 0.014)
    add_curve(
        f"HiRes_Bow_Bumper_Bridge_{side_name}",
        [(3.29, sign * 0.255, 0.735), (3.39, sign * 0.205, 0.765), (3.50, sign * 0.135, 0.790)],
        0.050,
        "MAGURA_W6_Rubber",
        INTACT_LOD0,
    )
    add_cyl(
        f"HiRes_Bow_Trim_Retainer_{side_name}",
        (3.315, sign * 0.275, 0.735), 0.030, 0.020,
        "MAGURA_W6_Hardware", INTACT_LOD0,
        rotation=(math.radians(90), 0.0, 0.0), vertices=32,
    )
    # Simplified LOD1 silhouette closeout so the gap does not reappear at range.
    add_wedge(f"HiRes_Bow_Closeout_LOD1_{side_name}", verts, faces, "MAGURA_W6_Hull", INTACT_LOD1, 0.0)

# ---------------------------------------------------------------------------
# 2. LAUNCHER / APU-73 FIDELITY. Keep rail and connector transforms fixed; add
#    real-looking channel edges, latch blocks, cable junctions, bolt detail and
#    bearing hardware to the already-proven rotating hierarchy.
# ---------------------------------------------------------------------------
az = bpy.data.objects.get("Launcher_Azimuth_Pivot")
el = bpy.data.objects.get("Launcher_Elevation_Pivot")
if az is None or el is None:
    raise RuntimeError("Proven launcher pivots missing")

# Soften only visible launcher mesh edges; no transforms or parenting changed.
for obj in list(bpy.data.objects):
    if obj.type != "MESH":
        continue
    if obj.name.startswith(("APU73_Rail_", "APU73_Upper_Guide_", "Launcher360_T_Crossbar", "Launcher360_Saddle_")):
        apply_bevel(obj, 0.006 if "Rail" in obj.name else 0.009, 3, 0.48)

# Rotary bearing and fastener ring on the moving head.
add_torus("HiRes_Launcher_Bearing_Ring", (-0.65, 0.0, 2.345), 0.205, 0.018, "MAGURA_W6_Hardware", parent=az)
for i in range(8):
    a = 2.0 * math.pi * i / 8.0
    add_cyl(
        f"HiRes_Launcher_Bearing_Bolt_{i:02d}",
        (-0.65 + math.cos(a) * 0.205, math.sin(a) * 0.205, 2.438),
        0.018, 0.024, "MAGURA_W6_Fasteners", vertices=24, parent=az,
    )

for side_name, y, sign in (("L", 0.64, 1.0), ("R", -0.64, -1.0)):
    outer_y = y + sign * 0.082
    # Thin fabricated side channel gives the launch rail a real aircraft-rail edge
    # instead of a monolithic rectangular extrusion.
    add_box(
        f"HiRes_APU73_SideChannel_{side_name}",
        (-0.65, outer_y, 2.555), (3.00, 0.026, 0.115),
        "MAGURA_W6_APU73_Rails", rotation=(0.0, -PITCH, 0.0), bevel=0.008, parent=el,
    )
    add_box(
        f"HiRes_APU73_LowerFlange_{side_name}",
        (-0.65, y, 2.493), (2.92, 0.175, 0.030),
        "MAGURA_W6_Hardware", rotation=(0.0, -PITCH, 0.0), bevel=0.006, parent=el,
    )
    # Rear electrical/umbilical box and forward latch housing.
    add_box(
        f"HiRes_APU73_UmbilicalBox_{side_name}",
        (-1.86, y + sign * 0.025, 2.330), (0.28, 0.205, 0.145),
        "MAGURA_W6_Hardware", rotation=(0.0, -PITCH, 0.0), bevel=0.018, parent=el,
    )
    add_box(
        f"HiRes_APU73_ForwardLatch_{side_name}",
        (0.64, y, 2.800), (0.22, 0.190, 0.120),
        "MAGURA_W6_Hardware", rotation=(0.0, -PITCH, 0.0), bevel=0.014, parent=el,
    )
    # Side fastener/rivet line and perforation rims.
    for j, x in enumerate((-1.82, -1.45, -1.08, -0.71, -0.34, 0.03, 0.40, 0.71)):
        z = 2.555 + math.tan(PITCH) * (x + 0.65)
        add_cyl(
            f"HiRes_APU73_SideBolt_{side_name}_{j:02d}",
            (x, outer_y + sign * 0.010, z), 0.018, 0.014,
            "MAGURA_W6_Fasteners", rotation=(math.radians(90), 0.0, 0.0), vertices=24, parent=el,
        )
    # Cable clips and exposed harness follow the lower rail side.
    cable_y = y + sign * 0.145
    add_curve(
        f"HiRes_APU73_Harness_{side_name}",
        [(-1.78, cable_y, 2.315), (-1.38, cable_y, 2.385), (-0.88, cable_y, 2.475), (-0.38, cable_y, 2.570), (0.10, cable_y, 2.655)],
        0.012, "MAGURA_W6_Cable", parent=el,
    )
    for j, x in enumerate((-1.48, -0.86, -0.24)):
        z = 2.405 + math.tan(PITCH) * (x + 1.38)
        add_torus(
            f"HiRes_APU73_CableClip_{side_name}_{j:02d}",
            (x, cable_y, z), 0.030, 0.006, "MAGURA_W6_Hardware",
            rotation=(math.radians(90), 0.0, 0.0), parent=el,
        )

# Static base flange bolt circle, also visual only.
for i in range(10):
    a = 2.0 * math.pi * i / 10.0
    add_cyl(
        f"HiRes_Pedestal_BaseBolt_{i:02d}",
        (-0.65 + math.cos(a) * 0.215, math.sin(a) * 0.215, 1.226),
        0.016, 0.020, "MAGURA_W6_Fasteners", vertices=24,
    )

# ---------------------------------------------------------------------------
# 3. MATERIAL / TEXTURE GLOW-UP. Bind unique high-resolution maps directly into
#    the EDM material graph so this HiRes shape can coexist without globally
#    replacing the original unit's texture filenames.
# ---------------------------------------------------------------------------
bindings = []

def dobind(matname, socket, filename, non_color=False):
    if bind(matname, socket, filename, non_color):
        bindings.append((matname, socket, filename))

# Hull composite / marine paint.
dobind("MAGURA_W6_Hull", "Base Color", "MAGURA_W6_Hull_Base_HiRes.png")
dobind("MAGURA_W6_Hull", "Normal (Non-Color)", "MAGURA_W6_Hull_Normal_HiRes.png", True)
dobind("MAGURA_W6_Hull", "RoughMet (Non-Color)", "MAGURA_W6_Hull_RoughMet_HiRes.png", True)
tune_default("MAGURA_W6_Hull", (0.025, 0.032, 0.037, 1.0), (0.78, 0.03, 0.0, 1.0))

# Armor and deck.
for matname in ("MAGURA_W6_Armor",):
    dobind(matname, "Base Color", "MAGURA_W6_Armor_Base_HiRes.png")
    dobind(matname, "RoughMet (Non-Color)", "MAGURA_W6_Armor_RoughMet_HiRes.png", True)
for matname in ("MAGURA_W6_Deck",):
    dobind(matname, "Base Color", "MAGURA_W6_Deck_Base_HiRes.png")
    dobind(matname, "RoughMet (Non-Color)", "MAGURA_W6_Deck_RoughMet_HiRes.png", True)

# Coated/parkerized exposed metal and launcher hardware.
metal_mats = (
    "MAGURA_W6_Hatches", "MAGURA_W6_Details", "MAGURA_W6_APU73_Rails",
    "MAGURA_W6_Hardware", "MAGURA_W6_Fasteners", "MAGURA_W6_EOIR",
    "MAGURA_W6_Weld", "MAGURA_W6_Chine_Wear", "MAGURA_W6_Exposed_Aluminum",
)
for matname in metal_mats:
    if bpy.data.materials.get(matname):
        dobind(matname, "Base Color", "MAGURA_W6_Metal_Base_HiRes.png")
        dobind(matname, "RoughMet (Non-Color)", "MAGURA_W6_Metal_RoughMet_HiRes.png", True)

# Destroyed skin gets a dedicated char/abraded map while retaining the same
# gameplay damage model and arguments.
for matname in ("MAGURA_W6_Damage", "MAGURA_W6_Damage_Metal", "MAGURA_W6_Peeled_Skin"):
    if bpy.data.materials.get(matname):
        dobind(matname, "Base Color", "MAGURA_W6_Damage_Base_HiRes.png")
        dobind(matname, "RoughMet (Non-Color)", "MAGURA_W6_Metal_RoughMet_HiRes.png", True)

# EO/IR optics and instrumental glass.
if bpy.data.materials.get("MAGURA_W6_Coated_Optics"):
    dobind("MAGURA_W6_Coated_Optics", "Base Color", "MAGURA_W6_Optics_Base_HiRes.png")
    dobind("MAGURA_W6_Coated_Optics", "RoughMet (Non-Color)", "MAGURA_W6_Optics_RoughMet_HiRes.png", True)
if bpy.data.materials.get("MAGURA_W6_Sensor_Glass"):
    dobind("MAGURA_W6_Sensor_Glass", "Glass Color (Color Filter)", "MAGURA_W6_Glass_Filter_HiRes.png")
    dobind("MAGURA_W6_Sensor_Glass", "Diffuse Color (Dirt)", "MAGURA_W6_Glass_Filter_HiRes.png")
    dobind("MAGURA_W6_Sensor_Glass", "RoughMet (Non-Color)", "MAGURA_W6_Optics_RoughMet_HiRes.png", True)

# ---------------------------------------------------------------------------
# 4. FUNCTION-FREEZE QA. Every protected connector/pivot matrix must be exactly
#    where FIX3 left it across starboard, neutral and port animation samples.
# ---------------------------------------------------------------------------
after = protected_snapshot()
max_delta = 0.0
for key, before_m in before.items():
    delta = matrix_max_delta(before_m, after[key])
    max_delta = max(max_delta, delta)
    if delta > 1.0e-6:
        raise RuntimeError(f"FUNCTIONAL TRANSFORM CHANGED {key}: max matrix delta {delta}")

# Explicit neutral launch-axis checks retained from FIX3 QA.
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
for name in ("POINT_R73_L", "POINT_R73_R", "POINT_LAUNCHER_AIM"):
    obj = bpy.data.objects[name]
    _, rot, _ = obj.matrix_world.decompose()
    axis = rot @ Vector((1.0, 0.0, 0.0))
    if axis.x < 0.90:
        raise RuntimeError(f"HiRes patch disturbed proven forward launch axis: {name}")

tri_after = count_triangles((INTACT_LOD0, INTACT_LOD1))
report = {
    "status": "visual_patch_success",
    "base": "exact live-proven MAGURA FIX3 blend / FIX5 geometry baseline",
    "protected_objects": list(PROTECTED),
    "sample_frames": list(SAMPLE_FRAMES),
    "max_protected_matrix_delta": max_delta,
    "intact_triangles_before": tri_before,
    "intact_triangles_after": tri_after,
    "visual_triangles_added": tri_after - tri_before,
    "bow_closeout": "port and starboard skin wedges + continuous rubber bumper bridges",
    "launcher_detail": "beveled APU-73 edges, fabricated side channels, latch/umbilical boxes, fasteners, harnesses, bearing hardware",
    "texture_bindings": bindings,
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print("MAGURA_HIRES_VISUAL_PATCH_READY=1")
print(json.dumps(report, indent=2))
