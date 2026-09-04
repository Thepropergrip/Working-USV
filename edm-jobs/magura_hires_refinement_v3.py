import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

# MAGURA HiRes V3 close-up correction.
#
# This pass intentionally replaces the V1/V2 additive bow overlays which proved
# visually wrong in DCS (detached/floating rods, remaining daylight seams).
# It also replaces the visible square bow bumper with a dense rounded equivalent
# at the exact same transform and applies conservative normal cleanup to visual
# hull/fender pieces.  Functional launcher/sensor/connectors remain frozen.

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
REPORT = ROOT / "hires-generated" / "visual-qa.json"
LOD0 = "MAGURA_LOD_0_90"
LOD1 = "MAGURA_LOD_1_250"

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


def snapshot():
    snap = {}
    for frame in SAMPLE_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name in PROTECTED:
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise RuntimeError(f"Protected object missing: {name}")
            snap[(frame, name)] = obj.matrix_world.copy()
    bpy.context.scene.frame_set(100)
    bpy.context.view_layer.update()
    return snap


def matrix_delta(a, b):
    return max(abs(a[r][c] - b[r][c]) for r in range(4) for c in range(4))


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifier(obj, mod):
    activate(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)


def weighted_normals(obj, keep_sharp=True):
    if obj is None or obj.type != "MESH":
        return False
    for poly in obj.data.polygons:
        poly.use_smooth = True
    try:
        mod = obj.modifiers.new(name="HiResV3_WeightedNormals", type="WEIGHTED_NORMAL")
        mod.keep_sharp = keep_sharp
        mod.weight = 100
        apply_modifier(obj, mod)
    except Exception as exc:
        print(f"HIRESV3_WEIGHTED_NORMAL_WARN {obj.name}: {exc}")
    return True


def bevel(obj, width, segments=10, angle=0.40):
    if obj is None or obj.type != "MESH":
        return False
    mod = obj.modifiers.new(name="HiResV3_Bevel", type="BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = angle
    mod.harden_normals = True
    apply_modifier(obj, mod)
    weighted_normals(obj, True)
    return True


def set_mat(obj, mat_name):
    obj.data.materials.clear()
    obj.data.materials.append(material(mat_name))


def move_to_collection(obj, colname):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection(colname).objects.link(obj)


def add_prism(name, sections, mat_name, colname=LOD0, bevel_width=0.0, smooth=True):
    # sections: [(x, half_width_y, z_bottom, z_top), ...]
    verts = []
    for x, hy, zb, zt in sections:
        verts.extend([
            (x, +hy, zb),
            (x, -hy, zb),
            (x, +hy, zt),
            (x, -hy, zt),
        ])
    faces = []
    # rear cap
    faces.extend([(0, 1, 3, 2)])
    for s in range(len(sections) - 1):
        a = s * 4
        b = (s + 1) * 4
        # bottom, top, port, starboard
        faces.extend([
            (a + 0, b + 0, b + 1, a + 1),
            (a + 2, a + 3, b + 3, b + 2),
            (a + 0, a + 2, b + 2, b + 0),
            (a + 1, b + 1, b + 3, a + 3),
        ])
    end = (len(sections) - 1) * 4
    faces.append((end + 0, end + 2, end + 3, end + 1))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection(colname).objects.link(obj)
    set_mat(obj, mat_name)
    for p in obj.data.polygons:
        p.use_smooth = smooth
    if bevel_width > 0:
        bevel(obj, bevel_width, segments=10, angle=0.30)
    elif smooth:
        weighted_normals(obj, True)
    return obj


def add_side_pad(name, sign, mat_name="MAGURA_W6_Rubber", colname=LOD0):
    # Embedded, broad rubber pad that bridges side fender to nose; unlike V1/V2
    # curves this is a solid flush prism, intentionally penetrating the hull skin
    # slightly so it cannot appear detached or leave daylight at the seam.
    y0_outer = sign * 0.405
    y0_inner = sign * 0.285
    y1_outer = sign * 0.285
    y1_inner = sign * 0.165
    verts = [
        (3.10, y0_outer, 0.690), (3.10, y0_inner, 0.690),
        (3.10, y0_outer, 0.805), (3.10, y0_inner, 0.805),
        (3.49, y1_outer, 0.710), (3.49, y1_inner, 0.710),
        (3.49, y1_outer, 0.825), (3.49, y1_inner, 0.825),
    ]
    # correct winding for sign does not matter with two-sided EDM materials, but
    # keep a closed manifold either way.
    faces = [
        (0, 4, 5, 1), (2, 3, 7, 6),
        (0, 2, 6, 4), (1, 5, 7, 3),
        (0, 1, 3, 2), (4, 6, 7, 5),
    ]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection(colname).objects.link(obj)
    set_mat(obj, mat_name)
    for p in obj.data.polygons:
        p.use_smooth = True
    bevel(obj, 0.022, segments=10, angle=0.28)
    return obj


def replace_bumper():
    old = bpy.data.objects.get("Bow_Rubber_Nose_Block")
    if old is None or old.type != "MESH":
        return False, None
    loc = old.matrix_world.translation.copy()
    rot = old.matrix_world.to_quaternion().copy()
    dims = old.dimensions.copy()
    mats = [m for m in old.data.materials if m]
    # Remove old visual mesh after preserving its exact transform/dimensions.
    bpy.data.objects.remove(old, do_unlink=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.name = "Bow_Rubber_Nose_Block"
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = rot
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, LOD0)
    if mats:
        obj.data.materials.clear()
        obj.data.materials.append(mats[0])
    else:
        set_mat(obj, "MAGURA_W6_Rubber")
    # Dense real roundover: many segments, then weighted normals. No diagonal
    # triangle shading should remain on the visible planar faces.
    width = min(0.032, float(min(dims)) * 0.16)
    bevel(obj, width, segments=16, angle=0.20)
    return True, [float(v) for v in dims]


before = snapshot()
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

# 1) Remove every prior experimental bow overlay that caused floating pieces.
removed = []
for obj in list(bpy.data.objects):
    if obj.name.startswith(("HiRes_Bow_", "HiResV2_Bow_")):
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)

# 2) One continuous embedded bow skin. It overlaps the original bow shell enough
# to mask the two jagged openings without any free-standing rods/bridges.
cap = add_prism(
    "HiResV3_Continuous_Bow_Fairing",
    [
        (3.08, 0.405, 0.565, 0.930),
        (3.30, 0.360, 0.585, 0.925),
        (3.50, 0.285, 0.615, 0.900),
        (3.61, 0.235, 0.645, 0.875),
    ],
    "MAGURA_W6_Hull", LOD0, bevel_width=0.018, smooth=True,
)
# LOD1 uses same solid silhouette but no costly bevel.
cap_lod1 = add_prism(
    "HiResV3_Continuous_Bow_Fairing_LOD1",
    [
        (3.08, 0.405, 0.565, 0.930),
        (3.30, 0.360, 0.585, 0.925),
        (3.50, 0.285, 0.615, 0.900),
        (3.61, 0.235, 0.645, 0.875),
    ],
    "MAGURA_W6_Hull", LOD1, bevel_width=0.0, smooth=False,
)

# 3) Flush solid side rubber pads, embedded into the new fairing and existing
# rub rail. These replace the visibly floating cylindrical curves.
pad_port = add_side_pad("HiResV3_Bow_Fender_Extension_Port", +1.0)
pad_stbd = add_side_pad("HiResV3_Bow_Fender_Extension_Starboard", -1.0)

# 4) Replace square nose bumper using exact original transform/dimensions but a
# dense rounded mesh, not a coarse low-segment block.
bumper_replaced, bumper_dims = replace_bumper()

# 5) Geometry-normal cleanup on the actual hull/rubrail parts. Vertex positions
# are untouched here; texture V3 separately removes the over-strong periodic
# normal pattern which was the main stern-radius wrinkle source.
normal_targets = (
    "AFT_HULL", "PORT_HULL", "STBD_HULL", "BOW_HULL",
    "W6_Production_Hull", "Forward_Deck", "Aft_Deck",
    "Bow_Fender_Cheek_Port", "Bow_Fender_Cheek_Starboard",
    "Bow_Lower_Rubrail_Fairing_Port", "Bow_Lower_Rubrail_Fairing_Starboard",
)
normal_fixed = []
for name in normal_targets:
    obj = bpy.data.objects.get(name)
    if obj is not None and weighted_normals(obj, True):
        normal_fixed.append(name)

# Hard functional freeze.
after = snapshot()
max_delta = 0.0
for key, m0 in before.items():
    d = matrix_delta(m0, after[key])
    max_delta = max(max_delta, d)
    if d > 1.0e-6:
        raise RuntimeError(f"FUNCTIONAL TRANSFORM CHANGED {key}: {d}")

report = {}
if REPORT.exists():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
report["refinement_v3"] = {
    "status": "success",
    "purpose": "remove floating bow overlays; continuous sealed bow fairing; dense bumper; stern/radius wrinkle correction",
    "removed_bad_bow_overlay_objects": removed,
    "continuous_bow_fairing": cap.name,
    "continuous_bow_fairing_lod1": cap_lod1.name,
    "flush_fender_extensions": [pad_port.name, pad_stbd.name],
    "bow_bumper_replaced_dense": bumper_replaced,
    "bow_bumper_dims_preserved": bumper_dims,
    "normal_cleanup_targets": normal_fixed,
    "functional_transform_max_delta": max_delta,
    "policy": "visual-only; protected turret/sensor/connector matrices unchanged",
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print("MAGURA_HIRES_REFINEMENT_V3_READY=1")
print(json.dumps(report["refinement_v3"], indent=2))
