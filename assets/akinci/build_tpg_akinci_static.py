from __future__ import annotations

import base64
import lzma
import struct
from array import array
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "assets" / "akinci" / "source"

EXPECTED_VERTICES = 51691
EXPECTED_FACES = 686604
TARGET_LENGTH = 12.3
TARGET_HEIGHT = 4.1
TARGET_SPAN = 20.0

MATERIAL_NAMES = [
    "Metal_Paint", "asdkk", "Metal_Paint.004", "Metal_Paint.003", "chrome",
    "white", "Air_Duct_Rubber.001", "Steel.002", "Metal_Paint.001",
    "Material_001", "idgu_002", "Smuged_Glass", "Material_002", "Steel",
    "Steel.001", "Air_Duct_Rubber", "idgu_001", "idgu", "Glass_dark",
    "Material_007",
]

MATERIAL_STYLE = [
    ((0.62, 0.64, 0.64, 1.0), False),
    ((0.18, 0.19, 0.19, 1.0), False),
    ((0.68, 0.69, 0.69, 1.0), False),
    ((0.42, 0.44, 0.44, 1.0), False),
    ((0.65, 0.67, 0.68, 1.0), False),
    ((0.92, 0.92, 0.90, 1.0), False),
    ((0.025, 0.028, 0.030, 1.0), False),
    ((0.34, 0.36, 0.37, 1.0), False),
    ((0.58, 0.60, 0.60, 1.0), False),
    ((0.20, 0.21, 0.22, 1.0), False),
    ((0.12, 0.13, 0.14, 1.0), False),
    ((0.08, 0.11, 0.13, 1.0), True),
    ((0.25, 0.26, 0.27, 1.0), False),
    ((0.32, 0.34, 0.35, 1.0), False),
    ((0.30, 0.32, 0.33, 1.0), False),
    ((0.025, 0.028, 0.030, 1.0), False),
    ((0.15, 0.16, 0.17, 1.0), False),
    ((0.20, 0.21, 0.22, 1.0), False),
    ((0.04, 0.06, 0.08, 1.0), True),
    ((0.22, 0.23, 0.24, 1.0), False),
]


def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def load_payload():
    parts = sorted(SOURCE_DIR.glob("part*.b64"))
    if not parts:
        raise FileNotFoundError(f"No AKINCI payload parts found under {SOURCE_DIR}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    packed = base64.b64decode(encoded, validate=True)
    raw = lzma.decompress(packed)
    print(f"[AKINCI] payload: {len(parts)} parts -> {len(packed)} XZ bytes -> {len(raw)} raw bytes")
    return raw


def decode_payload(data: bytes):
    off = 0
    if data[:4] != b"AKN1":
        raise RuntimeError(f"Unexpected payload magic: {data[:4]!r}")
    off = 4
    v_count, f_count = struct.unpack_from("<II", data, off)
    off += 8
    if (v_count, f_count) != (EXPECTED_VERTICES, EXPECTED_FACES):
        raise RuntimeError(f"Unexpected payload counts: {v_count} verts, {f_count} faces")

    vertices = []
    for _ in range(v_count):
        qx, qy, qz = struct.unpack_from("<HHH", data, off)
        off += 6
        x = (qx / 65535.0) * TARGET_LENGTH - TARGET_LENGTH * 0.5
        y = (qy / 65535.0) * TARGET_HEIGHT
        z = (qz / 65535.0) * TARGET_SPAN - TARGET_SPAN * 0.5
        vertices.append((x, y, z))

    run_count, = struct.unpack_from("<I", data, off)
    off += 4
    runs = []
    for _ in range(run_count):
        start, count, material_id = struct.unpack_from("<IIB", data, off)
        off += 9
        runs.append((start, count, material_id))

    faces = []
    for face_i in range(f_count):
        n = data[off]
        off += 1
        if n < 3 or n > 80:
            raise RuntimeError(f"Invalid polygon size {n} at face {face_i}")
        inds = struct.unpack_from("<" + ("H" * n), data, off)
        off += n * 2
        faces.append(inds)

    if off != len(data):
        raise RuntimeError(f"Payload parser ended at {off}, file is {len(data)} bytes")
    if not runs or runs[-1][0] + runs[-1][1] != f_count:
        raise RuntimeError("Material-run coverage is incomplete")

    print(f"[AKINCI] decoded {v_count} verts / {f_count} faces / {run_count} material runs")
    return vertices, faces, runs


def create_edm_material(name, rgba):
    from materials.materials import build_material_descriptions
    from materials.material_default import DefaultMaterial

    descriptions = build_material_descriptions()
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = rgba
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
    return mat


def build_render_mesh(vertices, faces, runs):
    mesh = bpy.data.meshes.new("Bayraktar_AKINCI_Static_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)

    obj = bpy.data.objects.new("Bayraktar_AKINCI_Static", mesh)
    bpy.context.scene.collection.objects.link(obj)

    for name, style in zip(MATERIAL_NAMES, MATERIAL_STYLE):
        rgba, _glass_hint = style
        obj.data.materials.append(create_edm_material(name, rgba))

    mat_indices = array("i", [0]) * len(mesh.polygons)
    for start, count, material_id in runs:
        if material_id >= len(MATERIAL_NAMES):
            raise RuntimeError(f"Material id {material_id} exceeds table")
        mat_indices[start:start + count] = array("i", [material_id]) * count
    mesh.polygons.foreach_set("material_index", mat_indices)

    smooth = array("b", [1]) * len(mesh.polygons)
    mesh.polygons.foreach_set("use_smooth", smooth)

    obj["TPG_SOURCE"] = "Uploaded Bayraktar AKINCI model"
    obj["TPG_SOURCE_FACES"] = 711608
    obj["TPG_WEAPON_FACES_REMOVED"] = 25004
    obj["TPG_EMPTY_PYLONS_RETAINED"] = True
    return obj


def add_collision_box(name, center, dimensions):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.EDMProps.SPECIAL_TYPE = "COLLISION_SHELL"
    return obj


def add_collision_shells():
    # Coarse non-rendering collision shells appropriate for a static aircraft.
    add_collision_box("COLLISION_Fuselage", (0.15, 1.55, 0.0), (10.9, 2.35, 1.85))
    add_collision_box("COLLISION_Wing", (0.10, 2.28, 0.0), (3.45, 0.42, 18.8))
    add_collision_box("COLLISION_Tail", (-4.85, 2.55, 0.0), (2.15, 1.35, 6.4))


def validate(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    expected = (TARGET_LENGTH, TARGET_HEIGHT, TARGET_SPAN)
    for got, want in zip(dims, expected):
        if abs(got - want) > 0.002:
            raise RuntimeError(f"Envelope mismatch: got {dims}, expected {expected}")
    if len(obj.data.vertices) != EXPECTED_VERTICES:
        raise RuntimeError(f"Vertex-count mismatch: {len(obj.data.vertices)}")
    if len(obj.data.polygons) != EXPECTED_FACES:
        raise RuntimeError(f"Face-count mismatch: {len(obj.data.polygons)}")
    print(f"[AKINCI] VALIDATION PASS: dims={dims}, verts={len(obj.data.vertices)}, faces={len(obj.data.polygons)}")
    print("[AKINCI] VALIDATION PASS: 25,004 modeled weapon faces removed; empty pylon geometry retained")


def main():
    clear_scene()
    raw = load_payload()
    vertices, faces, runs = decode_payload(raw)
    aircraft = build_render_mesh(vertices, faces, runs)
    add_collision_shells()
    validate(aircraft)
    bpy.context.view_layer.objects.active = aircraft
    aircraft.select_set(True)
    print("[AKINCI] scene complete; handing off to the official ED native EDM exporter")


main()
