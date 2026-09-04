import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

# Visual-only refinement layered on top of the proven HiRes patch.
# This pass responds directly to in-DCS close-up QA:
#   1) remove stern ripple/wrinkle shading,
#   2) fully close the remaining bow-side seam/opening,
#   3) remove faceted/diagonal shading on the square bow bumper,
#   4) clean visible faceting on forward hull/block surfaces.
#
# HARD RULE: no connector, pivot, animation, collision, weapon, sensor, WS/LN,
# bounding-box or gameplay-functional transform is changed.

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
    # Smooth the surface normals without moving any vertices. This is the key
    # stern-ripple fix: preserve exact silhouette, remove triangulation striping.
    for poly in obj.data.polygons:
        poly.use_smooth = True
    try:
        mod = obj.modifiers.new(name="HiResV2_WeightedNormals", type="WEIGHTED_NORMAL")
        mod.keep_sharp = keep_sharp
        mod.weight = 75
        apply_modifier(obj, mod)
    except Exception as exc:
        print(f"HIRESV2_WEIGHTED_NORMAL_WARN {obj.name}: {exc}")
    return True


def bevel_refine(obj, width, segments=8, angle=0.42):
    if obj is None or obj.type != "MESH":
        return False
    mod = obj.modifiers.new(name="HiResV2_Roundover", type="BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = angle
    mod.harden_normals = True
    apply_modifier(obj, mod)
    weighted_normals(obj, keep_sharp=True)
    return True


def set_mat(obj, mat_name):
    obj.data.materials.clear()
    obj.data.materials.append(material(mat_name))


def add_wedge(name, verts, faces, mat_name, colname=LOD0, bevel=0.0):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection(colname).objects.link(obj)
    set_mat(obj, mat_name)
    # Keep broad planar closeout faces flat; only the outer edges get rounded.
    for poly in obj.data.polygons:
        poly.use_smooth = False
    if bevel > 0:
        mod = obj.modifiers.new(name="HiResV2_CloseoutBevel", type="BEVEL")
        mod.width = bevel
        mod.segments = 6
        mod.limit_method = "ANGLE"
        mod.angle_limit = 0.35
        mod.harden_normals = True
        apply_modifier(obj, mod)
        weighted_normals(obj, keep_sharp=True)
    return obj


def add_curve(name, points, radius, mat_name, colname=LOD0):
    curve = bpy.data.curves.new(name + "_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 12
    curve.bevel_depth = radius
    curve.bevel_resolution = 8
    curve.resolution_u = 12
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    collection(colname).objects.link(obj)
    curve.materials.append(material(mat_name))
    return obj


def world_dims(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))


before = snapshot()
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

# ---------------------------------------------------------------------------
# A. STERN / HULL SHADING CLEANUP
# Do not move vertices. Replace coarse triangulation shading with weighted smooth
# normals on the visible LOD0 hull pieces. This preserves the exact hull shape.
# ---------------------------------------------------------------------------
normal_targets = (
    "AFT_HULL",
    "PORT_HULL",
    "STBD_HULL",
    "BOW_HULL",
    "W6_Production_Hull",
    "Forward_Deck",
    "Aft_Deck",
)
normal_fixed = []
for name in normal_targets:
    obj = bpy.data.objects.get(name)
    if obj and weighted_normals(obj):
        normal_fixed.append(name)

# ---------------------------------------------------------------------------
# B. SQUARE BOW NOSE BLOCK / BUMPER
# The in-DCS front block showed diagonal/faceted lines. Give the existing visual
# bumper a much denser rounded edge and weighted normals; position/scale unchanged.
# ---------------------------------------------------------------------------
bumper = bpy.data.objects.get("Bow_Rubber_Nose_Block")
bumper_refined = False
bumper_dims = None
if bumper and bumper.type == "MESH":
    bumper_dims = world_dims(bumper)
    min_dim = max(0.01, min(bumper_dims))
    # Conservative roundover: enough segments to eliminate visible angle lines,
    # but never large enough to alter the block's overall identity/silhouette.
    width = min(0.055, min_dim * 0.18)
    bumper_refined = bevel_refine(bumper, width=width, segments=10, angle=0.35)

# ---------------------------------------------------------------------------
# C. FULL BOW SEAM CLOSEOUT V2
# The first closeout was too narrow from close oblique views. Add a deeper skin
# seal and a wider continuous rubber bridge that overlaps both the side fender
# termination and nose block. These are render-only meshes in visual LODs.
# ---------------------------------------------------------------------------
closeout_names = []
for side_name, sign in (("Port", 1.0), ("Starboard", -1.0)):
    # Wider/deeper 3D skin patch than V1. It sits just inside the rubber bridge
    # and extends farther aft/front to ensure there is no daylight seam.
    verts = [
        (3.205, sign * 0.345, 0.835),
        (3.200, sign * 0.345, 0.595),
        (3.590, sign * 0.205, 0.895),
        (3.585, sign * 0.205, 0.625),
        (3.205, sign * 0.105, 0.815),
        (3.200, sign * 0.105, 0.615),
        (3.590, sign * 0.055, 0.870),
        (3.585, sign * 0.055, 0.650),
    ]
    faces = [
        (0, 2, 3, 1), (4, 5, 7, 6), (0, 4, 6, 2),
        (1, 3, 7, 5), (0, 1, 5, 4), (2, 6, 7, 3),
    ]
    obj = add_wedge(
        f"HiResV2_Bow_Seam_Seal_{side_name}",
        verts, faces, "MAGURA_W6_Hull", LOD0, bevel=0.010,
    )
    closeout_names.append(obj.name)

    bridge = add_curve(
        f"HiResV2_Bow_Rubber_Overlap_{side_name}",
        [
            (3.215, sign * 0.315, 0.740),
            (3.305, sign * 0.285, 0.755),
            (3.405, sign * 0.225, 0.775),
            (3.505, sign * 0.145, 0.792),
            (3.585, sign * 0.075, 0.800),
        ],
        0.066,
        "MAGURA_W6_Rubber",
        LOD0,
    )
    closeout_names.append(bridge.name)

    # LOD1 gets the same larger sealed silhouette so the seam cannot pop back in.
    obj1 = add_wedge(
        f"HiResV2_Bow_Seam_Seal_LOD1_{side_name}",
        verts, faces, "MAGURA_W6_Hull", LOD1, bevel=0.0,
    )
    closeout_names.append(obj1.name)

# ---------------------------------------------------------------------------
# D. FORWARD BOX / FACET CLEANUP
# Apply normals-only cleanup to compact forward visual meshes. No transforms.
# ---------------------------------------------------------------------------
forward_extra = []
for obj in list(bpy.data.objects):
    if obj.type != "MESH":
        continue
    if obj.name in PROTECTED:
        continue
    if obj.name.startswith(("Bow_", "Forward_")) and obj.name not in normal_fixed:
        if weighted_normals(obj):
            forward_extra.append(obj.name)

# ---------------------------------------------------------------------------
# FUNCTION FREEZE QA
# ---------------------------------------------------------------------------
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
report["refinement_v2"] = {
    "status": "success",
    "purpose": "stern wrinkle shading cleanup + full bow seam closure + bumper facet cleanup",
    "functional_transform_max_delta": max_delta,
    "normal_only_targets": normal_fixed,
    "forward_extra_normal_targets": forward_extra,
    "bow_bumper_refined": bumper_refined,
    "bow_bumper_world_dims": bumper_dims,
    "bow_seam_v2_objects": closeout_names,
    "policy": "visual meshes/material normals only; protected launcher/sensor/connectors unchanged",
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print("MAGURA_HIRES_REFINEMENT_V2_READY=1")
print(json.dumps(report["refinement_v2"], indent=2))
