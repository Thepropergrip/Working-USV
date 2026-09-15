from __future__ import annotations

import lzma
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
ASSET_XZ = WORKSPACE / "edm-jobs" / "assets" / "NATO_Shelter_V2.obj.xz"
ASSET_OBJ = WORKSPACE / "edm-jobs" / "assets" / "NATO_Shelter_V2.obj"
ASSET_MTL = WORKSPACE / "edm-jobs" / "assets" / "NATO_Shelter_V2.mtl"

EXPECTED_OVERALL_LENGTH_M = 50.0502
DOOR_ARG = 4
DOOR_TRANSITION_SEC = 8.0


def norm_name(s: str) -> str:
    return "".join(ch.lower() for ch in s if ch.isalnum())


def ensure_obj() -> Path:
    if not ASSET_XZ.exists():
        raise FileNotFoundError(f"Missing source asset: {ASSET_XZ}")
    with lzma.open(ASSET_XZ, "rb") as src, ASSET_OBJ.open("wb") as dst:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
    ASSET_MTL.write_text("""newmtl DOOR_Global_V2\nKd 0.5 0.5 0.5\n\nnewmtl MUR_DOOR_DETAIL_INTERIEUR_V2\nKd 0.5 0.5 0.5\n\nnewmtl SOL_MURET_HOUSE_PLAK_V2\nKd 0.5 0.5 0.5\n\nnewmtl SHELTER_EXTERIEUR_V2\nKd 0.5 0.5 0.5\n\nnewmtl Shelter_INTERIEUR_V2\nKd 0.5 0.5 0.5\n""", encoding="utf-8")
    return ASSET_OBJ


def all_meshes():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def top_level(objects):
    object_set = set(objects)
    return [o for o in objects if o.parent not in object_set]


def apply_global_matrix(objects, matrix: Matrix):
    roots = top_level(objects)
    for obj in roots:
        obj.matrix_world = matrix @ obj.matrix_world
    bpy.context.view_layer.update()


def world_bounds(objects):
    pts = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(corner))
    if not pts:
        raise RuntimeError("No mesh bounds available")
    mins = Vector((min(p[i] for p in pts) for i in range(3)))
    maxs = Vector((max(p[i] for p in pts) for i in range(3)))
    return mins, maxs


def obj_bounds(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mins = Vector((min(p[i] for p in pts) for i in range(3)))
    maxs = Vector((max(p[i] for p in pts) for i in range(3)))
    return mins, maxs


def center_of(obj):
    lo, hi = obj_bounds(obj)
    return (lo + hi) * 0.5


def locate(substr: str, required=True):
    n = norm_name(substr)
    candidates = [o for o in bpy.context.scene.objects if n in norm_name(o.name)]
    if not candidates:
        if required:
            raise RuntimeError(f"Could not locate object matching {substr!r}; objects={sorted(o.name for o in bpy.context.scene.objects)}")
        return None
    candidates.sort(key=lambda o: len(o.name))
    return candidates[0]


def parent_keep_world(child, parent):
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw


def orient_and_scale_source(source_objects):
    lo, hi = world_bounds(source_objects)
    ext = hi - lo
    vertical_axis = min(range(3), key=lambda i: ext[i])
    if vertical_axis == 1:
        apply_global_matrix(source_objects, Matrix.Rotation(math.radians(90), 4, "X"))
    elif vertical_axis == 0:
        apply_global_matrix(source_objects, Matrix.Rotation(math.radians(-90), 4, "Y"))

    lo, hi = world_bounds(source_objects)
    ext = hi - lo
    if ext[1] > ext[0]:
        apply_global_matrix(source_objects, Matrix.Rotation(math.radians(-90), 4, "Z"))

    lo, hi = world_bounds(source_objects)
    ext = hi - lo
    scale = EXPECTED_OVERALL_LENGTH_M / max(ext[0], ext[1])
    if not (0.97 <= scale <= 1.03):
        apply_global_matrix(source_objects, Matrix.Scale(scale, 4))

    left = locate("Exterieur DOOR Big AV Left")
    right = locate("Exterieur DOOR Big AV Right")
    meshes = [o for o in source_objects if o.type == "MESH"]
    source_center_x = sum((obj_bounds(o)[0].x + obj_bounds(o)[1].x) * 0.5 for o in meshes) / max(1, len(meshes))
    if (center_of(left).x + center_of(right).x) * 0.5 < source_center_x:
        apply_global_matrix(source_objects, Matrix.Rotation(math.pi, 4, "Z"))

    lo, hi = world_bounds(source_objects)
    apply_global_matrix(source_objects, Matrix.Translation((0.0, 0.0, -lo.z)))
    bpy.context.view_layer.update()


def source_material_role(name: str) -> str:
    n = norm_name(name)
    if "doorglobalv2" in n:
        return "door"
    if "murdoordetailinterieurv2" in n:
        return "murdoor"
    if "shelterexterieurv2" in n:
        return "exterior"
    if "shelterinterieurv2" in n:
        return "interior"
    if "solmurethouseplakv2" in n:
        return "ground"
    return "exterior"


TEXTURES = {
    "door": {"base": "DOOR_Global_V2_BaseColor.png", "normal": "DOOR_Global_V2_Normal.png", "rmo": "DOOR_Global_V2_OcclusionRoughnessMetallic.png"},
    "murdoor": {"base": "MUR DOOR DETAIL INTERIEUR_V2_BaseColor.png", "normal": "MUR DOOR DETAIL INTERIEUR_V2_Normal.png", "rmo": "MUR DOOR DETAIL INTERIEUR_V2_OcclusionRoughnessMetallic.png", "emissive": "MUR DOOR DETAIL INTERIEUR_V2_Emissive.png"},
    "exterior": {"base": "SHELTER_EXTERIEUR_V2_BaseColor.png", "normal": "SHELTER_EXTERIEUR_V2_Normal.png", "rmo": "SHELTER_EXTERIEUR_V2_OcclusionRoughnessMetallic.png", "emissive": "SHELTER_EXTERIEUR_V2_Emissive.png"},
    "interior": {"base": "Shelter_INTERIEUR_V2_BaseColor.png", "normal": "Shelter_INTERIEUR_V2_Normal.png", "rmo": "Shelter_INTERIEUR_V2_OcclusionRoughnessMetallic.png"},
    "ground": {"base": "SOL MURET HOUSE PLAK_V2_BaseColor.png", "normal": "SOL MURET HOUSE PLAK_V2_Normal.png", "rmo": "SOL MURET HOUSE PLAK_V2_OcclusionRoughnessMetallic.png"},
}


def create_edm_material(role: str):
    from materials.material_default import DefaultMaterial
    from materials.materials import build_material_descriptions
    from enums import NodeSocketInDefaultEnum

    name = f"TPG_NATO_SHELTER_{role.upper()}"
    existing = bpy.data.materials.get(name)
    if existing:
        return existing

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    desc = build_material_descriptions()[DefaultMaterial.name]
    group = nodes.new(type=DefaultMaterial.node_group_name)
    group.post_init(desc)
    group.name = f"EDM_Default_{role}"

    def attach(filename: str, socket_enum, non_color=False):
        if not filename:
            return
        img = bpy.data.images.get(filename)
        if img is None:
            img = bpy.data.images.new(filename, width=1, height=1, alpha=True)
        if non_color:
            try:
                img.colorspace_settings.name = "Non-Color"
            except Exception:
                pass
        tex = nodes.new("ShaderNodeTexImage")
        tex.name = f"TEX_{Path(filename).stem}"
        tex.image = img
        socket_name = socket_enum.value if hasattr(socket_enum, "value") else str(socket_enum)
        sock = group.inputs.get(socket_name)
        if sock is None:
            raise RuntimeError(f"EDM default material socket not found: {socket_name}")
        links.new(tex.outputs["Color"], sock)

    texs = TEXTURES[role]
    attach(texs.get("base"), NodeSocketInDefaultEnum.BASE_COLOR, False)
    attach(texs.get("normal"), NodeSocketInDefaultEnum.NORMAL, True)
    attach(texs.get("rmo"), NodeSocketInDefaultEnum.ROUGH_METAL, True)
    if texs.get("emissive"):
        attach(texs["emissive"], NodeSocketInDefaultEnum.EMISSIVE, False)
        emissive_value_name = NodeSocketInDefaultEnum.EMISSIVE_VALUE.value
        if group.inputs.get(emissive_value_name):
            group.inputs[emissive_value_name].default_value = 1.0
    return mat


def convert_materials(source_objects):
    role_mats = {role: create_edm_material(role) for role in TEXTURES}
    for obj in source_objects:
        if obj.type != "MESH":
            continue
        try:
            obj.EDMProps.TWO_SIDED = True
        except Exception:
            pass
        for slot in obj.material_slots:
            old = slot.material
            role = source_material_role(old.name if old else "")
            slot.material = role_mats[role]


def new_empty(name: str, location):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.8
    bpy.context.scene.collection.objects.link(obj)
    return obj


def animate_door_pivot(pivot, close_degrees: float):
    action = bpy.data.actions.new(f"{DOOR_ARG}_{pivot.name}_ALARM_STATE")
    pivot.animation_data_create()
    pivot.animation_data.action = action
    pivot.rotation_mode = "XYZ"
    for frame, deg in ((0, 0.0), (100, 0.0), (200, close_degrees)):
        pivot.rotation_euler.z = math.radians(deg)
        pivot.keyframe_insert("rotation_euler", frame=frame, group="DCS Argument")
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"


def make_collision_box(name: str, center, dims, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (dims[0] * 0.5, dims[1] * 0.5, dims[2] * 0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.EDMProps.SPECIAL_TYPE = "COLLISION_SHELL"
    obj.display_type = "WIRE"
    obj.hide_render = True
    if parent is not None:
        parent_keep_world(obj, parent)
    return obj


def build_front_door_animation():
    left = locate("Exterieur DOOR Big AV Left")
    right = locate("Exterieur DOOR Big AV Right")
    result = []
    for label, door in (("LEFT", left), ("RIGHT", right)):
        lo, hi = obj_bounds(door)
        c = (lo + hi) * 0.5
        hinge_x = lo.x
        pivot = new_empty(f"NATO_FRONT_DOOR_{label}_PIVOT", (hinge_x, c.y, c.z))
        parent_keep_world(door, pivot)
        close_deg = -90.0 if c.y > 0 else 90.0
        animate_door_pivot(pivot, close_deg)
        dims = hi - lo
        collider = make_collision_box(
            f"COLLISION_SHELL_FRONT_DOOR_{label}", c,
            (max(0.25, dims.x), max(0.28, min(0.55, dims.y)), max(0.25, dims.z)),
            parent=pivot,
        )
        result.append((door, pivot, collider, lo, hi))
    return result


def build_fixed_hardened_shell(door_data):
    shelter = locate("Shelter Global")
    slo, shi = obj_bounds(shelter)
    door_centers = [center_of(item[0]) for item in door_data]
    hinge_x = sum(item[3].x for item in door_data) / len(door_data)
    cavity_half = min(abs(c.y) for c in door_centers) - 0.18
    door_top = max(item[4].z for item in door_data)
    roof_bottom = door_top + 0.18

    rear_left = locate("Interieur Door Left")
    rear_right = locate("Interieur Door Right")
    rear_x = (center_of(rear_left).x + center_of(rear_right).x) * 0.5

    outer_half = max(abs(slo.y), abs(shi.y))
    top = shi.z
    body_front = hinge_x + 0.05
    body_rear = rear_x - 0.35
    body_len = max(1.0, body_front - body_rear)
    body_center_x = (body_front + body_rear) * 0.5
    side_width = max(0.6, outer_half - cavity_half)
    side_center_abs_y = cavity_half + side_width * 0.5
    lower_height = max(1.0, roof_bottom)
    lower_center_z = lower_height * 0.5

    make_collision_box("COLLISION_SHELL_FIXED_LEFT", (body_center_x, side_center_abs_y, lower_center_z), (body_len, side_width, lower_height))
    make_collision_box("COLLISION_SHELL_FIXED_RIGHT", (body_center_x, -side_center_abs_y, lower_center_z), (body_len, side_width, lower_height))

    roof_height = max(0.5, top - roof_bottom)
    make_collision_box("COLLISION_SHELL_FIXED_ROOF", (body_center_x, 0.0, roof_bottom + roof_height * 0.5), (body_len, outer_half * 2.0, roof_height))
    make_collision_box("COLLISION_SHELL_FIXED_REAR", (rear_x, 0.0, lower_center_z), (0.65, cavity_half * 2.0, lower_height))

    return {"cavity_half": cavity_half, "roof_bottom": roof_bottom, "rear_x": rear_x, "front_x": hinge_x, "outer_half": outer_half, "top": top}


def validate_animation(door_data, shell_info):
    bpy.context.scene.frame_set(100)
    bpy.context.view_layer.update()
    open_centers = [center_of(item[2]) for item in door_data]
    if not all(abs(c.y) > shell_info["cavity_half"] * 0.65 for c in open_centers):
        raise RuntimeError(f"Open door collision does not clear entrance: {open_centers}")

    bpy.context.scene.frame_set(200)
    bpy.context.view_layer.update()
    closed_centers = [center_of(item[2]) for item in door_data]
    if not all(abs(c.x - shell_info["front_x"]) < 1.0 for c in closed_centers):
        raise RuntimeError(f"Closed blast doors are not on front plane: {closed_centers}")
    y_extents = [obj_bounds(item[2]) for item in door_data]
    pos_ok = any(center_of(item[2]).y > 0 and obj_bounds(item[2])[0].y <= 0.30 for item in door_data)
    neg_ok = any(center_of(item[2]).y < 0 and obj_bounds(item[2])[1].y >= -0.30 for item in door_data)
    if not (pos_ok and neg_ok):
        raise RuntimeError(f"Closed blast doors leave excessive center gap: {[(tuple(lo), tuple(hi)) for lo,hi in y_extents]}")

    bpy.context.scene.frame_set(100)
    bpy.context.view_layer.update()


def cleanup_import_helpers():
    for obj in list(bpy.context.scene.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    obj_path = ensure_obj()
    bpy.ops.wm.obj_import(filepath=str(obj_path), up_axis="Y", forward_axis="NEGATIVE_Z", use_split_objects=True, use_split_groups=False, validate_meshes=True)
    cleanup_import_helpers()
    source_objects = list(bpy.context.scene.objects)
    if not any(o.type == "MESH" for o in source_objects):
        raise RuntimeError("OBJ import produced no meshes")

    orient_and_scale_source(source_objects)
    convert_materials(source_objects)
    door_data = build_front_door_animation()
    shell_info = build_fixed_hardened_shell(door_data)
    validate_animation(door_data, shell_info)

    origin = new_empty("NATO_SHELTER_MODEL_ORIGIN", (0.0, 0.0, 0.0))
    try:
        origin.EDMProps.SPECIAL_TYPE = "CONNECTOR"
        origin.EDMProps.CONNECTOR_EXT = ""
    except Exception:
        pass

    bpy.context.scene.frame_set(100)
    bpy.context.view_layer.update()
    lo, hi = world_bounds([o for o in bpy.context.scene.objects if o.type == "MESH" and not norm_name(o.name).startswith("collisionshell")])
    print("NATO_SHELTER_BUILD_OK")
    print(f"visual_bounds_m min={tuple(round(v,3) for v in lo)} max={tuple(round(v,3) for v in hi)}")
    print(f"bay_clear_halfwidth_m={shell_info['cavity_half']:.3f} roof_under_m={shell_info['roof_bottom']:.3f}")
    print(f"alarm_arg={DOOR_ARG} green_frame=100 open red_frame=200 closed transition_hint_s={DOOR_TRANSITION_SEC}")


if __name__ == "__main__":
    main()
