import json
import os
from pathlib import Path

import bpy
import numpy as np

# MAGURA HiRes V4 corrective pass.
# Rejects the V3 close-up result and aggressively removes the failure modes seen
# in DCS: floating additive detail, corrugated/wrinkled hull shading, and smooth-
# shaded rectangular components. This remains VISUAL ONLY.

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
TEXDIR = ROOT / "hires-generated" / "textures"
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


def clear_custom_normals_and_recalc(obj):
    if obj is None or obj.type != "MESH":
        return False
    activate(obj)
    try:
        # Clear custom split normals left by weighted-normal modifiers when Blender
        # exposes the operator. Failure is non-fatal; recalc below is authoritative.
        if hasattr(bpy.ops.mesh, "customdata_custom_splitnormals_clear"):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception as exc:
        print(f"V4_CLEAR_CUSTOM_NORMALS_WARN {obj.name}: {exc}")
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception as exc:
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        print(f"V4_RECALC_NORMALS_WARN {obj.name}: {exc}")
    obj.select_set(False)
    obj.data.update()
    return True


def shade_smooth_clean(obj):
    if not clear_custom_normals_and_recalc(obj):
        return False
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.update()
    return True


def shade_flat_clean(obj):
    if not clear_custom_normals_and_recalc(obj):
        return False
    for p in obj.data.polygons:
        p.use_smooth = False
    obj.data.update()
    return True


def set_mat(obj, mat_name):
    obj.data.materials.clear()
    obj.data.materials.append(material(mat_name))


def image(name, filename):
    img = bpy.data.images.get(name)
    path = TEXDIR / filename
    if img is None:
        if not path.exists():
            raise RuntimeError(f"Required V4 texture missing: {path}")
        img = bpy.data.images.load(str(path), check_existing=False)
        img.name = name
    img.filepath = str(path)
    return img, path


def save_pixels(img, path, arr):
    img.pixels.foreach_set(arr.reshape(-1).astype(np.float32))
    img.update()
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()


def flatten_hull_material_textures():
    # Completely remove tangent-space normal deformation. V3 retained 6%; the
    # DCS close-up still showed radial wrinkles, so V4 deliberately uses a true
    # flat normal and lets geometry + roughness provide shape.
    normal_img, normal_path = image("MAGURA_W6_Hull_Normal_HiRes", "MAGURA_W6_Hull_Normal_HiRes.png")
    w, h = normal_img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    normal_img.pixels.foreach_get(px)
    a = px.reshape((h, w, 4))
    a[:, :, 0] = 0.5
    a[:, :, 1] = 0.5
    a[:, :, 2] = 1.0
    a[:, :, 3] = 1.0
    save_pixels(normal_img, normal_path, a)

    # Kill most of the repeating visible weave/color modulation on the hull. The
    # finish should read as painted marine composite, not exposed corrugated cloth.
    base_img, base_path = image("MAGURA_W6_Hull_Base_HiRes", "MAGURA_W6_Hull_Base_HiRes.png")
    w, h = base_img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    base_img.pixels.foreach_get(px)
    a = px.reshape((h, w, 4))
    mean_rgb = a[:, :, :3].mean(axis=(0, 1), keepdims=True)
    keep = 0.20
    a[:, :, :3] = mean_rgb * (1.0 - keep) + a[:, :, :3] * keep
    a[:, :, 3] = 1.0
    save_pixels(base_img, base_path, a)

    # Reduce roughness striping as well so highlights stay broad and clean around
    # stern/bow radii instead of breaking into ribs.
    rm_img, rm_path = image("MAGURA_W6_Hull_RoughMet_HiRes", "MAGURA_W6_Hull_RoughMet_HiRes.png")
    w, h = rm_img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    rm_img.pixels.foreach_get(px)
    a = px.reshape((h, w, 4))
    mean_rgb = a[:, :, :3].mean(axis=(0, 1), keepdims=True)
    keep_rm = 0.25
    a[:, :, :3] = mean_rgb * (1.0 - keep_rm) + a[:, :, :3] * keep_rm
    a[:, :, 3] = 1.0
    save_pixels(rm_img, rm_path, a)

    # Hard-disable the normal texture link in the actual EDM hull material too.
    # This prevents exporter/material interpretation from reintroducing it.
    mat = material("MAGURA_W6_Hull")
    normal_unlinked = False
    if mat.use_nodes and mat.node_tree:
        for node in mat.node_tree.nodes:
            if not hasattr(node, "inputs") or "Normal (Non-Color)" not in node.inputs:
                continue
            socket = node.inputs["Normal (Non-Color)"]
            for link in list(mat.node_tree.links):
                if link.to_socket == socket:
                    mat.node_tree.links.remove(link)
                    normal_unlinked = True
            try:
                socket.default_value = (0.5, 0.5, 1.0, 1.0)
            except Exception:
                pass
    return {
        "flat_normal": True,
        "normal_link_removed": normal_unlinked,
        "hull_base_variation_keep": keep,
        "hull_roughmet_variation_keep": keep_rm,
    }


def remove_all_additive_hires_objects():
    # The floating parts in V3 came from additive detail experiments. V4 removes
    # ALL previous HiRes helper/detail geometry and then adds back exactly one
    # bow fairing. Existing proven base meshes remain, including applied rail
    # edge bevels/material upgrades from the core pass.
    prefixes = ("HiRes_", "HiResV2_", "HiResV3_", "HiResV4_")
    removed = []
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def create_v4_bow_fairing():
    # One closed manifold visual fairing only. No free-standing bridge rods,
    # retainers, bolt circles, harnesses or floating detail. Dense longitudinal
    # sections let the side curvature read smoothly without a normal map.
    sections = []
    count = 17
    for i in range(count):
        t = i / (count - 1)
        x = 3.055 + 0.570 * t
        hy = 0.430 * (1.0 - t) + 0.205 * t
        zb = 0.555 * (1.0 - t) + 0.650 * t
        zt = 0.935 * (1.0 - t) + 0.875 * t
        sections.append((x, hy, zb, zt))

    verts = []
    for x, hy, zb, zt in sections:
        verts.extend([(x, +hy, zb), (x, -hy, zb), (x, +hy, zt), (x, -hy, zt)])

    faces = []
    smooth_flags = []
    faces.append((0, 1, 3, 2)); smooth_flags.append(False)
    for s in range(len(sections) - 1):
        a = s * 4
        b = (s + 1) * 4
        # bottom, top, port, starboard. Only curved sides smooth.
        faces.extend([
            (a + 0, b + 0, b + 1, a + 1),
            (a + 2, a + 3, b + 3, b + 2),
            (a + 0, a + 2, b + 2, b + 0),
            (a + 1, b + 1, b + 3, a + 3),
        ])
        smooth_flags.extend([False, False, True, True])
    e = (len(sections) - 1) * 4
    faces.append((e + 0, e + 2, e + 3, e + 1)); smooth_flags.append(False)

    mesh = bpy.data.meshes.new("HiResV4_Continuous_Bow_Fairing_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("HiResV4_Continuous_Bow_Fairing", mesh)
    collection(LOD0).objects.link(obj)
    set_mat(obj, "MAGURA_W6_Hull")
    for p, smooth in zip(mesh.polygons, smooth_flags):
        p.use_smooth = smooth
    clear_custom_normals_and_recalc(obj)

    # LOD1 sealed silhouette with the same closed geometry; no smoothing trickery.
    mesh1 = bpy.data.meshes.new("HiResV4_Continuous_Bow_Fairing_LOD1_Mesh")
    mesh1.from_pydata(verts, [], faces)
    mesh1.update()
    obj1 = bpy.data.objects.new("HiResV4_Continuous_Bow_Fairing_LOD1", mesh1)
    collection(LOD1).objects.link(obj1)
    set_mat(obj1, "MAGURA_W6_Hull")
    for p in mesh1.polygons:
        p.use_smooth = False
    clear_custom_normals_and_recalc(obj1)
    return [obj.name, obj1.name]


def fix_hull_shading():
    # Curved composite/fender parts: remove weighted/custom normal artifacts and
    # use ordinary smooth vertex normals. Do NOT bevel or subdivide the geometry.
    exact = (
        "AFT_HULL", "PORT_HULL", "STBD_HULL", "BOW_HULL", "W6_Production_Hull",
        "Bow_Fender_Cheek_Port", "Bow_Fender_Cheek_Starboard",
        "Bow_Lower_Rubrail_Fairing_Port", "Bow_Lower_Rubrail_Fairing_Starboard",
    )
    fixed = []
    for name in exact:
        obj = bpy.data.objects.get(name)
        if obj and shade_smooth_clean(obj):
            fixed.append(name)
    return fixed


def fix_hard_surface_shading():
    # Rectangular/hard-surface components should never carry interpolated round
    # shading across broad planar faces. This directly removes the 'radius lines'
    # seen on boxes, panels and rails in DCS.
    tokens = (
        "Box", "Panel", "Hatch", "Rail", "Bracket", "Plate", "Block",
        "Crossbar", "Saddle", "Console", "Armor", "Deck", "Housing",
    )
    curved_exclusions = (
        "Hull", "Fender", "Rubrail", "EOIR", "Sensor", "Optic", "Lens",
        "Sphere", "Torus", "Ring", "Cylinder", "Mast", "Pole",
    )
    fixed = []
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or obj.name in PROTECTED:
            continue
        if any(tok in obj.name for tok in curved_exclusions):
            continue
        if obj.name == "Bow_Rubber_Nose_Block" or any(tok in obj.name for tok in tokens):
            if shade_flat_clean(obj):
                fixed.append(obj.name)
    return fixed


before = snapshot()
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

removed_additive = remove_all_additive_hires_objects()
material_cleanup = flatten_hull_material_textures()
hull_fixed = fix_hull_shading()
hard_fixed = fix_hard_surface_shading()
bow_objects = create_v4_bow_fairing()

# Final guarantee: no experimental HiRes helpers remain beyond the two intended
# V4 fairing meshes.
remaining_hires_objects = sorted(
    obj.name for obj in bpy.data.objects
    if obj.name.startswith(("HiRes_", "HiResV2_", "HiResV3_", "HiResV4_"))
)
expected = sorted(bow_objects)
if remaining_hires_objects != expected:
    raise RuntimeError(
        "Unexpected additive HiRes objects remain after V4 cleanup: "
        f"expected={expected} actual={remaining_hires_objects}"
    )

# Hard functional freeze across known live-proven animation samples.
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
report["refinement_v4"] = {
    "status": "success",
    "purpose": "remove all floating additive detail; hard-surface flat shading; eliminate stern/radius wrinkles",
    "removed_additive_hires_objects": removed_additive,
    "remaining_additive_hires_objects": remaining_hires_objects,
    "material_cleanup": material_cleanup,
    "hull_smooth_normal_cleanup": hull_fixed,
    "hard_surface_flat_shading_cleanup": hard_fixed,
    "bow_fairing_objects": bow_objects,
    "functional_transform_max_delta": max_delta,
    "policy": "visual-only; protected turret/sensor/connector matrices unchanged; no gameplay Lua changes",
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print("MAGURA_HIRES_REFINEMENT_V4_READY=1")
print(json.dumps(report["refinement_v4"], indent=2))
