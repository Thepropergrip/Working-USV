from __future__ import annotations

import base64
import lzma
import struct
from array import array
from pathlib import Path
import bpy

SOURCE_DIR = Path(__file__).resolve().parent / "source"

EXPECTED_VERTICES = 45135
EXPECTED_FACES = 62024
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
MATERIAL_COLORS = [
    (0.62,0.64,0.64,1.0),(0.18,0.19,0.19,1.0),(0.68,0.69,0.69,1.0),
    (0.42,0.44,0.44,1.0),(0.65,0.67,0.68,1.0),(0.92,0.92,0.90,1.0),
    (0.025,0.028,0.030,1.0),(0.34,0.36,0.37,1.0),(0.58,0.60,0.60,1.0),
    (0.20,0.21,0.22,1.0),(0.12,0.13,0.14,1.0),(0.08,0.11,0.13,1.0),
    (0.25,0.26,0.27,1.0),(0.32,0.34,0.35,1.0),(0.30,0.32,0.33,1.0),
    (0.025,0.028,0.030,1.0),(0.15,0.16,0.17,1.0),(0.20,0.21,0.22,1.0),
    (0.04,0.06,0.08,1.0),(0.22,0.23,0.24,1.0),
]

def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def read_uvarint(data, off):
    value = 0
    shift = 0
    while True:
        b = data[off]
        off += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, off
        shift += 7
        if shift > 35:
            raise RuntimeError("Malformed varint")

def read_svarint(data, off):
    u, off = read_uvarint(data, off)
    return ((u >> 1) ^ -(u & 1)), off

def load_payload():
    parts = sorted(SOURCE_DIR.glob("part*.b64"))
    if not parts:
        raise FileNotFoundError(f"No AKINCI source parts in {SOURCE_DIR}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    packed = base64.b64decode(encoded, validate=True)
    raw = lzma.decompress(packed)
    print(f"[AKINCI] loaded {len(parts)} source parts; {len(packed)} compressed bytes")
    return raw

def decode_payload(data):
    if data[:4] != b"AKN5":
        raise RuntimeError(f"Bad AKINCI payload magic: {data[:4]!r}")
    off = 4
    v_count, f_count = struct.unpack_from("<II", data, off)
    off += 8
    if (v_count, f_count) != (EXPECTED_VERTICES, EXPECTED_FACES):
        raise RuntimeError(f"Payload count mismatch: {v_count} verts, {f_count} faces")

    qverts = []
    first = struct.unpack_from("<HHH", data, off)
    off += 6
    qverts.append(first)
    prev = first
    for _ in range(1, v_count):
        dx, off = read_svarint(data, off)
        dy, off = read_svarint(data, off)
        dz, off = read_svarint(data, off)
        cur = (prev[0] + dx, prev[1] + dy, prev[2] + dz)
        qverts.append(cur)
        prev = cur

    vertices = [
        ((qx / 65535.0) * TARGET_LENGTH - TARGET_LENGTH * 0.5,
         (qy / 65535.0) * TARGET_HEIGHT,
         (qz / 65535.0) * TARGET_SPAN - TARGET_SPAN * 0.5)
        for qx, qy, qz in qverts
    ]

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
        first_index, off = read_uvarint(data, off)
        inds = [first_index]
        prev_index = first_index
        for _ in range(1, n):
            delta, off = read_svarint(data, off)
            prev_index += delta
            inds.append(prev_index)
        if min(inds) < 0 or max(inds) >= v_count:
            raise RuntimeError(f"Face {face_i} index outside vertex table")
        faces.append(tuple(inds))

    if off != len(data):
        raise RuntimeError(f"Payload parser ended at {off}; file length is {len(data)}")
    print(f"[AKINCI] decoded {v_count} vertices / {f_count} unique surface polygons / {run_count} material runs")
    return vertices, faces, runs

def create_edm_material(name, rgba):
    from materials.materials import build_material_descriptions
    from materials.material_default import DefaultMaterial
    descs = build_material_descriptions()
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = rgba
    mat.node_tree.nodes.clear()
    node = mat.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
    node.post_init(descs[DefaultMaterial.name])
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

    for name, rgba in zip(MATERIAL_NAMES, MATERIAL_COLORS):
        obj.data.materials.append(create_edm_material(name, rgba))

    mat_indices = array("i", [0]) * len(mesh.polygons)
    for start, count, material_id in runs:
        mat_indices[start:start+count] = array("i", [material_id]) * count
    mesh.polygons.foreach_set("material_index", mat_indices)
    mesh.polygons.foreach_set("use_smooth", array("b", [1]) * len(mesh.polygons))

    obj["TPG_ORIGINAL_SOURCE_FACES"] = 711608
    obj["TPG_WEAPON_FACES_REMOVED"] = 25004
    obj["TPG_DUPLICATE_POLYGONS_REMOVED"] = 624580
    obj["TPG_EMPTY_PYLONS_RETAINED"] = True
    return obj

def add_collision_box(name, center, dimensions):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.EDMProps.SPECIAL_TYPE = "COLLISION_SHELL"

def add_collision_shells():
    add_collision_box("COLLISION_Fuselage", (0.15,1.55,0.0), (10.9,2.35,1.85))
    add_collision_box("COLLISION_Wing", (0.10,2.28,0.0), (3.45,0.42,18.8))
    add_collision_box("COLLISION_Tail", (-4.85,2.55,0.0), (2.15,1.35,6.4))

def validate(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    dims = (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    expected = (TARGET_LENGTH, TARGET_HEIGHT, TARGET_SPAN)
    if any(abs(got-want) > 0.002 for got,want in zip(dims,expected)):
        raise RuntimeError(f"Envelope mismatch: {dims} vs {expected}")
    if len(obj.data.vertices) != EXPECTED_VERTICES or len(obj.data.polygons) != EXPECTED_FACES:
        raise RuntimeError("Final mesh count mismatch")
    print(f"[AKINCI] VALIDATION PASS dims={dims} verts={len(obj.data.vertices)} faces={len(obj.data.polygons)}")
    print("[AKINCI] weapons removed; empty pylons retained; duplicate coplanar source polygons removed")

def main():
    clear_scene()
    vertices, faces, runs = decode_payload(load_payload())
    aircraft = build_render_mesh(vertices, faces, runs)
    add_collision_shells()
    validate(aircraft)
    bpy.context.view_layer.objects.active = aircraft
    aircraft.select_set(True)
    print("[AKINCI] scene ready for native official ED EDM export")

main()
