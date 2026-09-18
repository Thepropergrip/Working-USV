from __future__ import annotations

import base64
import hashlib
import lzma
import math
import os
import struct
from array import array
from pathlib import Path

import bpy

SOURCE_DIR = Path(__file__).resolve().parent / "ply_source"

SOURCE_SHA256 = "06a7aa14d9c664ff85608053ea2029c4cd10c6682e527e87e7af3354c01841f6"
EXPECTED_SOURCE_VERTICES = 51691
EXPECTED_SOURCE_FACES = 711608
EXPECTED_WEAPON_FACES_REMOVED = 25004
EXPECTED_UNIQUE_FACES = 62768
EXPECTED_USED_VERTICES = 45135

TARGET_LENGTH = 12.3
TARGET_HEIGHT = 4.1
TARGET_SPAN = 20.0

REMOVE_FACE_RANGES = (
    (225250, 233827),
    (238446, 254673),
    (281962, 281967),
    (711413, 711604),
)

MATERIAL_NAMES = [
    "Metal_Paint",
    "asdkk",
    "Metal_Paint.004",
    "Metal_Paint.003",
    "chrome",
    "white",
    "Air_Duct_Rubber.001",
    "Steel.002",
    "Metal_Paint.001",
    "Материал.001",
    "идгу.002",
    "Smuged_Glass",
    "Материал.002",
    "Steel",
    "Steel.001",
    "Air_Duct_Rubber",
    "идгу.001",
    "идгу",
    "Glass_dark",
    "Материал.007",
]

MATERIAL_COLORS = [
    (0.62, 0.64, 0.64, 1.0),
    (0.18, 0.19, 0.19, 1.0),
    (0.68, 0.69, 0.69, 1.0),
    (0.42, 0.44, 0.44, 1.0),
    (0.48, 0.50, 0.51, 1.0),
    (0.92, 0.92, 0.90, 1.0),
    (0.025, 0.028, 0.030, 1.0),
    (0.34, 0.36, 0.37, 1.0),
    (0.58, 0.60, 0.60, 1.0),
    (0.30, 0.31, 0.31, 1.0),
    (0.22, 0.23, 0.23, 1.0),
    (0.08, 0.11, 0.13, 1.0),
    (0.36, 0.37, 0.37, 1.0),
    (0.32, 0.34, 0.35, 1.0),
    (0.30, 0.32, 0.33, 1.0),
    (0.025, 0.028, 0.030, 1.0),
    (0.22, 0.23, 0.23, 1.0),
    (0.22, 0.23, 0.23, 1.0),
    (0.025, 0.035, 0.045, 1.0),
    (0.15, 0.16, 0.16, 1.0),
]

MATERIAL_BLOCKS = (
    (0, 55587, 0),
    (55588, 234417, 1),
    (234418, 254673, 2),
    (254674, 254825, 3),
    (254826, 281967, 4),
    (281968, 302703, 5),
    (302704, 327279, 6),
    (327280, 406511, 7),
    (406512, 408431, 8),
    (408432, 412237, 9),
    (412238, 412749, 10),
    (412750, 412751, 11),
    (412752, 415855, 12),
    (415856, 593007, 13),
    (593008, 661103, 14),
    (661104, 710255, 15),
    (710256, 711412, 16),
    (711413, 711604, 17),
    (711605, 711606, 18),
    (711607, 711607, 19),
)


def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def load_ply_bytes():
    parts = sorted(SOURCE_DIR.glob("ply_part*.b64"))
    if len(parts) != 12:
        raise RuntimeError(f"Expected 12 PLY payload chunks, found {len(parts)}")

    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    packed = base64.b64decode(encoded, validate=True)
    raw = lzma.decompress(packed)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise RuntimeError(f"PLY SHA-256 mismatch: {digest}")

    print(
        f"[AKINCI] exact source PLY reconstructed: {len(parts)} chunks, "
        f"{len(packed)} XZ bytes -> {len(raw)} bytes, sha256={digest}"
    )
    return raw


def is_weapon_face(face_index):
    for lo, hi in REMOVE_FACE_RANGES:
        if lo <= face_index <= hi:
            return True
    return False


def parse_and_clean_ply(data):
    marker = b"end_header\n"
    header_end = data.find(marker)
    if header_end < 0:
        raise RuntimeError("PLY end_header not found")
    data_offset = header_end + len(marker)
    header = data[:data_offset].decode("ascii", errors="strict")

    if "format binary_little_endian 1.0" not in header:
        raise RuntimeError("Expected binary little-endian PLY")
    if f"element vertex {EXPECTED_SOURCE_VERTICES}" not in header:
        raise RuntimeError("Unexpected PLY vertex count")
    if f"element face {EXPECTED_SOURCE_FACES}" not in header:
        raise RuntimeError("Unexpected PLY face count")

    vertex_struct = struct.Struct("<8f")
    raw_vertices = []
    raw_normals = []
    raw_uvs = []

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")

    offset = data_offset
    for _ in range(EXPECTED_SOURCE_VERTICES):
        x, y, z, nx, ny, nz, u, v = vertex_struct.unpack_from(data, offset)
        offset += vertex_struct.size
        raw_vertices.append((x, y, z))
        raw_normals.append((nx, ny, nz))
        raw_uvs.append((u, v))

        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)
        min_z = min(min_z, z)
        max_z = max(max_z, z)

    sx = max_x - min_x
    sy = max_y - min_y
    sz = max_z - min_z
    cx = (min_x + max_x) * 0.5
    cz = (min_z + max_z) * 0.5

    scale_x = -(TARGET_LENGTH / sx)
    scale_y = TARGET_HEIGHT / sy
    scale_z = TARGET_SPAN / sz

    transformed_vertices = []
    transformed_normals = []

    for (x, y, z), (nx, ny, nz) in zip(raw_vertices, raw_normals):
        transformed_vertices.append((
            (x - cx) * scale_x,
            (y - min_y) * scale_y,
            (z - cz) * scale_z,
        ))

        # Inverse-transpose normal transform for the non-uniform axis scale.
        tx = nx / scale_x
        ty = ny / scale_y
        tz = nz / scale_z
        mag = math.sqrt(tx * tx + ty * ty + tz * tz)
        if mag > 1e-12:
            transformed_normals.append((tx / mag, ty / mag, tz / mag))
        else:
            transformed_normals.append((0.0, 1.0, 0.0))

    faces = []
    face_materials = []
    used_vertices = set()
    seen = set()

    material_block_index = 0
    removed_weapons = 0
    duplicate_faces = 0

    for face_index in range(EXPECTED_SOURCE_FACES):
        while (
            material_block_index + 1 < len(MATERIAL_BLOCKS)
            and face_index > MATERIAL_BLOCKS[material_block_index][1]
        ):
            material_block_index += 1

        block_lo, block_hi, material_id = MATERIAL_BLOCKS[material_block_index]
        if not (block_lo <= face_index <= block_hi):
            raise RuntimeError(f"No material block for face {face_index}")

        polygon_size = data[offset]
        offset += 1
        if polygon_size < 3:
            raise RuntimeError(f"Invalid PLY polygon size {polygon_size} at face {face_index}")

        indices = struct.unpack_from("<" + ("I" * polygon_size), data, offset)
        offset += polygon_size * 4

        if is_weapon_face(face_index):
            removed_weapons += 1
            continue

        # Drop only byte-for-byte duplicate polygons carrying the same material.
        # Winding changes, material changes and distinct topology are retained.
        key = (material_id, indices)
        if key in seen:
            duplicate_faces += 1
            continue
        seen.add(key)

        faces.append(indices)
        face_materials.append(material_id)
        used_vertices.update(indices)

    if offset != len(data):
        raise RuntimeError(f"PLY parser ended at {offset}; file length is {len(data)}")
    if removed_weapons != EXPECTED_WEAPON_FACES_REMOVED:
        raise RuntimeError(
            f"Weapon-face removal mismatch: {removed_weapons} vs "
            f"{EXPECTED_WEAPON_FACES_REMOVED}"
        )
    if len(faces) != EXPECTED_UNIQUE_FACES:
        raise RuntimeError(
            f"Unique-face count mismatch: {len(faces)} vs {EXPECTED_UNIQUE_FACES}"
        )
    if len(used_vertices) != EXPECTED_USED_VERTICES:
        raise RuntimeError(
            f"Used-vertex count mismatch: {len(used_vertices)} vs {EXPECTED_USED_VERTICES}"
        )

    used_sorted = sorted(used_vertices)
    remap = {old: new for new, old in enumerate(used_sorted)}

    vertices = [transformed_vertices[i] for i in used_sorted]
    normals = [transformed_normals[i] for i in used_sorted]
    uvs = [raw_uvs[i] for i in used_sorted]
    compact_faces = [tuple(remap[i] for i in face) for face in faces]

    print(
        f"[AKINCI] source={EXPECTED_SOURCE_FACES} faces; "
        f"weapons_removed={removed_weapons}; exact_duplicates_removed={duplicate_faces}; "
        f"final={len(compact_faces)} faces / {len(vertices)} vertices"
    )

    return vertices, normals, uvs, compact_faces, face_materials


def create_edm_material(name, rgba):
    from materials.materials import build_material_descriptions
    from materials.material_default import DefaultMaterial

    descriptions = build_material_descriptions()
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = rgba
    mat.roughness = 0.62
    mat.metallic = 0.0
    mat.node_tree.nodes.clear()

    node = mat.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
    node.post_init(descriptions[DefaultMaterial.name])

    base = node.inputs.get("Base Color")
    if base is not None:
        base.default_value = rgba

    alpha = node.inputs.get("Base Alpha*")
    if alpha is not None:
        alpha.default_value = 1.0

    opacity = node.inputs.get("Opacity Value")
    if opacity is not None:
        opacity.default_value = 1.0

    transparency = node.inputs.get("Transparency")
    if transparency is not None:
        try:
            transparency.default_value = "OPAQUE"
        except Exception:
            pass

    return mat


def build_render_mesh(vertices, normals, uvs, faces, face_materials):
    mesh = bpy.data.meshes.new("Bayraktar_AKINCI_Static_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)

    obj = bpy.data.objects.new("Bayraktar_AKINCI_Static", mesh)
    bpy.context.scene.collection.objects.link(obj)

    for name, rgba in zip(MATERIAL_NAMES, MATERIAL_COLORS):
        obj.data.materials.append(create_edm_material(name, rgba))

    mesh.polygons.foreach_set("material_index", array("i", face_materials))
    mesh.polygons.foreach_set("use_smooth", array("b", [1]) * len(mesh.polygons))

    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_flat = array("f")
    for loop in mesh.loops:
        u, v = uvs[loop.vertex_index]
        uv_flat.extend((u, v))
    uv_layer.data.foreach_set("uv", uv_flat)

    # Preserve the PLY's source shading normals when Blender exposes the API.
    try:
        mesh.normals_split_custom_set_from_vertices(normals)
        print("[AKINCI] source custom normals applied")
    except Exception as exc:
        print(f"[AKINCI] custom-normal API unavailable; smooth geometry normals used: {exc}")

    obj["TPG_SOURCE"] = "Exact uploaded binary PLY"
    obj["TPG_SOURCE_SHA256"] = SOURCE_SHA256
    obj["TPG_MODELED_WEAPONS_REMOVED"] = True
    obj["TPG_EMPTY_PYLONS_RETAINED"] = True
    obj["TPG_EXACT_DUPLICATE_FACES_REMOVED"] = (
        EXPECTED_SOURCE_FACES - EXPECTED_WEAPON_FACES_REMOVED - EXPECTED_UNIQUE_FACES
    )
    return obj


def add_collision_box(name, center, dimensions):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.EDMProps.SPECIAL_TYPE = "COLLISION_SHELL"


def add_collision_shells():
    add_collision_box("COLLISION_Fuselage", (0.15, 1.55, 0.0), (10.9, 2.35, 1.85))
    add_collision_box("COLLISION_Wing", (0.10, 2.28, 0.0), (3.45, 0.42, 18.8))
    add_collision_box("COLLISION_Tail", (-4.85, 2.55, 0.0), (2.15, 1.35, 6.4))


def validate(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    dims = (
        max(xs) - min(xs),
        max(ys) - min(ys),
        max(zs) - min(zs),
    )
    expected = (TARGET_LENGTH, TARGET_HEIGHT, TARGET_SPAN)

    if any(abs(got - want) > 0.002 for got, want in zip(dims, expected)):
        raise RuntimeError(f"Envelope mismatch: {dims} vs {expected}")
    if len(obj.data.vertices) != EXPECTED_USED_VERTICES:
        raise RuntimeError(
            f"Final vertex count {len(obj.data.vertices)} != {EXPECTED_USED_VERTICES}"
        )
    if len(obj.data.polygons) != EXPECTED_UNIQUE_FACES:
        raise RuntimeError(
            f"Final face count {len(obj.data.polygons)} != {EXPECTED_UNIQUE_FACES}"
        )

    print(
        f"[AKINCI] VALIDATION PASS dims={dims} "
        f"verts={len(obj.data.vertices)} faces={len(obj.data.polygons)}"
    )
    print("[AKINCI] exact source topology retained except modeled weapons and exact duplicates")


def main():
    clear_scene()
    vertices, normals, uvs, faces, face_materials = parse_and_clean_ply(load_ply_bytes())
    aircraft = build_render_mesh(vertices, normals, uvs, faces, face_materials)
    add_collision_shells()
    validate(aircraft)
    bpy.context.view_layer.objects.active = aircraft
    aircraft.select_set(True)
    print("[AKINCI] scene ready for native official ED EDM export")


main()
