from __future__ import annotations

import base64
import lzma
import struct
from array import array
from pathlib import Path

import bpy

SOURCE_DIR = Path(__file__).resolve().parent / "source_obj"

TARGET_LENGTH = 12.3
TARGET_HEIGHT = 4.1
TARGET_SPAN = 20.0

EXPECTED_PARTS = 25
EXPECTED_PACKED_MAGIC = b"AKN7"
EXPECTED_PACKED_VERTICES = 679119
EXPECTED_PACKED_META_COUNT = 677969
EXPECTED_FACES = 463129
EXPECTED_USED_VERTICES = 461609
EXPECTED_MATERIALS = 19

MATERIAL_COLORS = {
    "Metal_Paint": (0.62, 0.64, 0.64, 1.0),
    "asdkk": (0.18, 0.19, 0.19, 1.0),
    "Metal_Paint.004": (0.68, 0.69, 0.69, 1.0),
    "Metal_Paint.003": (0.42, 0.44, 0.44, 1.0),
    "chrome": (0.65, 0.67, 0.68, 1.0),
    "white": (0.92, 0.92, 0.90, 1.0),
    "Air_Duct_Rubber.001": (0.025, 0.028, 0.030, 1.0),
    "Steel.002": (0.34, 0.36, 0.37, 1.0),
    "Metal_Paint.001": (0.58, 0.60, 0.60, 1.0),
    "Материал.001": (0.30, 0.31, 0.31, 1.0),
    "идгу.002": (0.22, 0.23, 0.23, 1.0),
    "Smuged_Glass": (0.08, 0.11, 0.13, 0.48),
    "Материал.002": (0.36, 0.37, 0.37, 1.0),
    "Steel": (0.32, 0.34, 0.35, 1.0),
    "Steel.001": (0.30, 0.32, 0.33, 1.0),
    "Air_Duct_Rubber": (0.025, 0.028, 0.030, 1.0),
    "идгу.001": (0.22, 0.23, 0.23, 1.0),
    "Glass_dark": (0.025, 0.035, 0.045, 0.38),
    "Материал.007": (0.15, 0.16, 0.16, 1.0),
}


def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def reconstruct_payload():
    parts = sorted(SOURCE_DIR.glob("part*.b64"))
    if len(parts) != EXPECTED_PARTS:
        raise RuntimeError(f"Expected {EXPECTED_PARTS} AKINCI payload chunks, found {len(parts)}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    packed = base64.b64decode(encoded, validate=True)
    raw = lzma.decompress(packed)
    if raw[:4] != EXPECTED_PACKED_MAGIC:
        raise RuntimeError(f"Expected AKN7 payload, got {raw[:8]!r}")
    print(
        f"[AKINCI] payload reconstructed: {len(parts)} chunks, "
        f"{len(packed)} XZ bytes -> {len(raw)} AKN7 bytes"
    )
    return raw


def read_uvarint(data, offset):
    value = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise RuntimeError("Unexpected EOF while reading AKN7 varint")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, offset
        shift += 7
        if shift > 35:
            raise RuntimeError("AKN7 varint is too large")


def read_svarint(data, offset):
    value, offset = read_uvarint(data, offset)
    return ((value >> 1) ^ -(value & 1)), offset


def decode_akn7(raw):
    offset = 4
    vertex_count, meta_count, material_count = struct.unpack_from("<III", raw, offset)
    offset += 12

    if vertex_count != EXPECTED_PACKED_VERTICES:
        raise RuntimeError(f"AKN7 vertex count {vertex_count} != {EXPECTED_PACKED_VERTICES}")
    if meta_count != EXPECTED_PACKED_META_COUNT:
        raise RuntimeError(f"AKN7 metadata count {meta_count} != {EXPECTED_PACKED_META_COUNT}")
    if material_count != EXPECTED_MATERIALS:
        raise RuntimeError(f"AKN7 material count {material_count} != {EXPECTED_MATERIALS}")

    material_names = []
    for _ in range(material_count):
        name_len = struct.unpack_from("<H", raw, offset)[0]
        offset += 2
        material_names.append(raw[offset:offset + name_len].decode("utf-8"))
        offset += name_len

    missing_colors = [name for name in material_names if name not in MATERIAL_COLORS]
    if missing_colors:
        raise RuntimeError(f"No material colors defined for: {missing_colors}")

    quantized_offset = offset
    quantized_end = quantized_offset + vertex_count * 6
    if quantized_end > len(raw):
        raise RuntimeError("AKN7 vertex block is truncated")
    offset = quantized_end

    faces = []
    face_materials = []
    used_vertices = set()

    while offset < len(raw):
        if offset + 2 > len(raw):
            raise RuntimeError("Truncated AKN7 face header")
        polygon_size = raw[offset]
        material_id = raw[offset + 1]
        offset += 2

        if polygon_size < 3 or polygon_size > 255:
            raise RuntimeError(f"Invalid AKN7 polygon size {polygon_size}")
        if material_id >= material_count:
            raise RuntimeError(f"Invalid AKN7 material id {material_id}")

        first_index, offset = read_uvarint(raw, offset)
        indices = [first_index]
        previous = first_index
        for _ in range(1, polygon_size):
            delta, offset = read_svarint(raw, offset)
            previous += delta
            indices.append(previous)

        if min(indices) < 0 or max(indices) >= vertex_count:
            raise RuntimeError(
                f"AKN7 polygon index outside 0..{vertex_count - 1}: "
                f"{min(indices)}..{max(indices)}"
            )

        face = tuple(indices)
        faces.append(face)
        face_materials.append(material_id)
        used_vertices.update(face)

    if len(faces) != EXPECTED_FACES:
        raise RuntimeError(f"AKN7 face count {len(faces)} != {EXPECTED_FACES}")
    if len(used_vertices) != EXPECTED_USED_VERTICES:
        raise RuntimeError(
            f"AKN7 used-vertex count {len(used_vertices)} != {EXPECTED_USED_VERTICES}"
        )

    # Compact away the 217,510 unreferenced staging vertices while preserving the
    # exact quantized geometry represented by every retained polygon.
    used_sorted = sorted(used_vertices)
    remap = {old: new for new, old in enumerate(used_sorted)}
    compact_faces = [tuple(remap[i] for i in face) for face in faces]

    vertices = []
    qmins = [65535, 65535, 65535]
    qmaxs = [0, 0, 0]
    for old_index in used_sorted:
        qx, qy, qz = struct.unpack_from("<HHH", raw, quantized_offset + old_index * 6)
        qmins[0] = min(qmins[0], qx)
        qmins[1] = min(qmins[1], qy)
        qmins[2] = min(qmins[2], qz)
        qmaxs[0] = max(qmaxs[0], qx)
        qmaxs[1] = max(qmaxs[1], qy)
        qmaxs[2] = max(qmaxs[2], qz)

        x = (qx / 65535.0) * TARGET_LENGTH - TARGET_LENGTH * 0.5
        y = (qy / 65535.0) * TARGET_HEIGHT
        z = (qz / 65535.0) * TARGET_SPAN - TARGET_SPAN * 0.5
        vertices.append((x, y, z))

    if qmins != [0, 0, 0] or qmaxs != [65535, 65535, 65535]:
        raise RuntimeError(f"AKN7 compacted envelope lost extrema: min={qmins}, max={qmaxs}")

    print(
        f"[AKINCI] AKN7 decoded: packed_vertices={vertex_count}, "
        f"used_vertices={len(vertices)}, faces={len(compact_faces)}, "
        f"materials={material_count}, meta_count={meta_count}"
    )
    print(f"[AKINCI] material table: {material_names}")
    return vertices, compact_faces, face_materials, material_names


def create_edm_material(name, rgba):
    from materials.materials import build_material_descriptions
    from materials.material_default import DefaultMaterial

    descriptions = build_material_descriptions()
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    material.diffuse_color = rgba
    material.node_tree.nodes.clear()

    node = material.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
    node.post_init(descriptions[DefaultMaterial.name])

    base = node.inputs.get("Base Color")
    if base is not None:
        base.default_value = rgba

    alpha = node.inputs.get("Base Alpha*")
    if alpha is not None:
        alpha.default_value = rgba[3]

    opacity = node.inputs.get("Opacity Value")
    if opacity is not None:
        opacity.default_value = rgba[3]

    roughness = node.inputs.get("RoughMet R")
    if roughness is not None:
        if "chrome" in name.lower():
            roughness.default_value = 0.18
        elif "rubber" in name.lower():
            roughness.default_value = 0.82
        else:
            roughness.default_value = 0.48

    return material


def build_render_mesh(vertices, faces, face_materials, material_names):
    mesh = bpy.data.meshes.new("Bayraktar_AKINCI_Static_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)

    obj = bpy.data.objects.new("Bayraktar_AKINCI_Static", mesh)
    bpy.context.scene.collection.objects.link(obj)

    for name in material_names:
        obj.data.materials.append(create_edm_material(name, MATERIAL_COLORS[name]))

    mesh.polygons.foreach_set("material_index", array("i", face_materials))
    mesh.polygons.foreach_set("use_smooth", array("b", [1]) * len(mesh.polygons))

    obj["TPG_SOURCE"] = "AKN7 compact cleaned AKINCI geometry"
    obj["TPG_MODELED_WEAPONS_REMOVED"] = True
    obj["TPG_EMPTY_PYLONS_RETAINED"] = True
    obj["TPG_TARGET_LENGTH_M"] = TARGET_LENGTH
    obj["TPG_TARGET_HEIGHT_M"] = TARGET_HEIGHT
    obj["TPG_TARGET_SPAN_M"] = TARGET_SPAN
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
    dimensions = (
        max(xs) - min(xs),
        max(ys) - min(ys),
        max(zs) - min(zs),
    )
    expected = (TARGET_LENGTH, TARGET_HEIGHT, TARGET_SPAN)

    if any(abs(got - want) > 0.002 for got, want in zip(dimensions, expected)):
        raise RuntimeError(f"Envelope mismatch: {dimensions} vs {expected}")
    if len(obj.data.vertices) != EXPECTED_USED_VERTICES:
        raise RuntimeError(
            f"Final vertex count {len(obj.data.vertices)} != {EXPECTED_USED_VERTICES}"
        )
    if len(obj.data.polygons) != EXPECTED_FACES:
        raise RuntimeError(
            f"Final face count {len(obj.data.polygons)} != {EXPECTED_FACES}"
        )

    print(
        f"[AKINCI] VALIDATION PASS dims={dimensions} "
        f"verts={len(obj.data.vertices)} faces={len(obj.data.polygons)}"
    )
    print("[AKINCI] modeled stores removed; empty pylons retained")


def main():
    clear_scene()
    vertices, faces, face_materials, material_names = decode_akn7(reconstruct_payload())
    aircraft = build_render_mesh(vertices, faces, face_materials, material_names)
    add_collision_shells()
    validate(aircraft)
    bpy.context.view_layer.objects.active = aircraft
    aircraft.select_set(True)
    print("[AKINCI] scene ready for native official ED EDM export")


main()
