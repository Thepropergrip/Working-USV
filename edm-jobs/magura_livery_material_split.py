import json
import os
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
REPORT = ROOT / "magura-livery-material-qa.json"

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
HULL_OBJECTS = (
    "W6_Production_Hull",
    "W6_Hull_MAGURA_LOD_1_250",
    "W6_Hull_MAGURA_LOD_2_800",
    "W6_Hull_MAGURA_LOD_3_2500",
)
BOW_FAIRINGS = (
    "HiResV4_Continuous_Bow_Fairing",
    "HiResV4_Continuous_Bow_Fairing_LOD1",
)
TOP_MATERIAL = "MAGURA_W6_Fiberglass_Top"


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


def material(name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        raise RuntimeError(f"Required material missing: {name}")
    return mat


def find_shader(mat, socket_name):
    if not mat.use_nodes or not mat.node_tree:
        return None
    for node in mat.node_tree.nodes:
        if hasattr(node, "inputs") and socket_name in node.inputs:
            return node
    return None


def find_image(filename):
    stem = Path(filename).stem
    for img in bpy.data.images:
        if img.name == stem:
            return img
        try:
            if Path(bpy.path.abspath(img.filepath)).name == filename:
                return img
        except Exception:
            pass
    return None


def ensure_normal_texture_link(mat):
    shader = find_shader(mat, "Normal (Non-Color)")
    if shader is None:
        raise RuntimeError(f"{mat.name} has no EDM normal socket")
    socket = shader.inputs["Normal (Non-Color)"]
    if socket.is_linked:
        return True
    img = find_image("MAGURA_W6_Hull_Normal_HiRes_V5.png")
    if img is None:
        raise RuntimeError("V5 flat hull normal image not found in patched blend")
    node = mat.node_tree.nodes.new(type="ShaderNodeTexImage")
    node.name = "FiberglassTop_DefaultFlatNormal"
    node.image = img
    node.interpolation = "Linear"
    mat.node_tree.links.new(node.outputs["Color"], socket)
    return True


def ensure_top_material():
    old = bpy.data.materials.get(TOP_MATERIAL)
    if old is not None:
        bpy.data.materials.remove(old, do_unlink=True)
    top = material("MAGURA_W6_Hull").copy()
    top.name = TOP_MATERIAL
    ensure_normal_texture_link(top)
    return top


def set_single_material(obj, mat):
    if obj is None or obj.type != "MESH":
        return False
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.material_index = 0
    obj.data.update()
    return True


def assign_upper_fiberglass(obj, top_mat):
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Hull visual object missing: {obj}")
    hull_mat = material("MAGURA_W6_Hull")
    obj.data.materials.clear()
    obj.data.materials.append(hull_mat)
    obj.data.materials.append(top_mat)

    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_z = min(p.z for p in corners)
    max_z = max(p.z for p in corners)
    # Upper 30% of the actual hull envelope, restricted to surfaces facing at
    # least partly upward. This targets molded/fiberglass upper-body surfaces,
    # not the vertical hull sides or underside.
    z_cut = min_z + 0.70 * (max_z - min_z)
    normal_matrix = obj.matrix_world.to_3x3()
    selected = 0
    total = len(obj.data.polygons)
    for poly in obj.data.polygons:
        wc = obj.matrix_world @ poly.center
        wn = (normal_matrix @ poly.normal).normalized()
        use_top = wc.z >= z_cut and wn.z >= 0.12
        poly.material_index = 1 if use_top else 0
        if use_top:
            selected += 1
    if selected == 0:
        raise RuntimeError(f"No upper fiberglass faces selected on {obj.name}")
    obj.data.update()
    return {
        "object": obj.name,
        "total_polygons": total,
        "upper_fiberglass_polygons": selected,
        "z_cut": round(float(z_cut), 6),
        "min_z": round(float(min_z), 6),
        "max_z": round(float(max_z), 6),
    }


before = snapshot()
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

top_mat = ensure_top_material()
assignments = []
for name in HULL_OBJECTS:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Required hull LOD object missing: {name}")
    assignments.append(assign_upper_fiberglass(obj, top_mat))

# User requirement: the large square bow closeout/fairing stays black in every
# livery. It was previously part of MAGURA_W6_Hull and therefore inherited camo.
bow_black = []
for name in BOW_FAIRINGS:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Required bow fairing missing: {name}")
    if set_single_material(obj, material("MAGURA_W6_Hardware")):
        bow_black.append(name)

# Functional freeze.
after = snapshot()
max_delta = 0.0
for key, m0 in before.items():
    d = matrix_delta(m0, after[key])
    max_delta = max(max_delta, d)
    if d > 1.0e-6:
        raise RuntimeError(f"FUNCTIONAL TRANSFORM CHANGED {key}: {d}")

# Hard negative assertions: deck panels/hatches/fairings must NOT be assigned to
# the new fiberglass-top material.
forbidden = (
    "Forward_Deck", "Center_Deck", "Aft_Deck", "Forward_Access_Hatch",
    "Engine_Service_Hatch", "Launcher_Fairing_Port", "Launcher_Fairing_Starboard",
    "Cowl_Center_Spine", "Rail_Pedestal_L", "Rail_Pedestal_R",
)
for name in forbidden:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        continue
    mats = [m.name if m else None for m in obj.data.materials]
    if TOP_MATERIAL in mats:
        raise RuntimeError(f"Forbidden panel/metal object received fiberglass livery material: {name}")

report = {
    "status": "success",
    "top_material": TOP_MATERIAL,
    "upper_fiberglass_assignments": assignments,
    "bow_fairing_forced_black_material": bow_black,
    "forbidden_panel_objects_checked": list(forbidden),
    "functional_transform_max_delta": max_delta,
    "policy": "visual material partition only; no Lua/weapon/sensor/connector/animation changes",
}
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("MAGURA_LIVERY_MATERIAL_SPLIT_READY=1")
print(json.dumps(report, indent=2))
