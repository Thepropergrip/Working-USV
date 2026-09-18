from __future__ import annotations

import base64
import lzma
from array import array
from pathlib import Path
import bpy

SOURCE_DIR = Path(__file__).resolve().parent / "source_obj"

SOURCE_VERTICES = 51691
SOURCE_FACES = 711608
EXPECTED_WEAPON_FACES_REMOVED = 25004
EXPECTED_CLEAN_FACES = 62024
EXPECTED_CLEAN_VERTICES = 45135

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


def reconstruct_obj_bytes():
    parts = sorted(SOURCE_DIR.glob("part*.b64"))
    if not parts:
        raise FileNotFoundError(f"No staged AKINCI OBJ chunks in {SOURCE_DIR}")
    if len(parts) != 25:
        raise RuntimeError(f"Expected 25 AKINCI OBJ chunks, found {len(parts)}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    packed = base64.b64decode(encoded, validate=True)
    raw = lzma.decompress(packed)
    if not raw.lstrip().startswith((b"#", b"mtllib ", b"o ", b"v ")):
        raise RuntimeError("Decoded AKINCI source does not look like Wavefront OBJ")
    print(f"[AKINCI] reconstructed OBJ from {len(parts)} parts: {len(packed)} XZ bytes -> {len(raw)} raw bytes")
    return raw


def face_is_weapon(face_index):
    for lo, hi in REMOVE_FACE_RANGES:
        if lo <= face_index <= hi:
            return True
    return False


def parse_and_clean_obj(raw):
    vertices = []
    unique_faces = []
    face_materials = []
    seen = set()

    face_i = 0
    mat_block_i = 0
    removed_weapons = 0
    duplicate_faces = 0

    for line in raw.splitlines():
        if line.startswith(b"v "):
            fields = line.split()
            if len(fields) < 4:
                raise RuntimeError(f"Malformed OBJ vertex line: {line[:120]!r}")
            vertices.append((float(fields[1]), float(fields[2]), float(fields[3])))
            continue

        if not line.startswith(b"f "):
            continue

        while mat_block_i + 1 < len(MATERIAL_BLOCKS) and face_i > MATERIAL_BLOCKS[mat_block_i][1]:
            mat_block_i += 1
        lo, hi, material_id = MATERIAL_BLOCKS[mat_block_i]
        if not (lo <= face_i <= hi):
            raise RuntimeError(f"No material block for source face {face_i}")

        fields = line.split()[1:]
        inds = []
        for token in fields:
            vtxt = token.split(b"/", 1)[0]
            if not vtxt:
                raise RuntimeError(f"OBJ face {face_i} has an empty position index")
            idx = int(vtxt)
            if idx < 0:
                idx = len(vertices) + idx
            else:
                idx -= 1
            if idx < 0 or idx >= len(vertices):
                raise RuntimeError(f"OBJ face {face_i} vertex index {idx} outside {len(vertices)} vertices")
            inds.append(idx)

        if len(inds) < 3:
            raise RuntimeError(f"OBJ face {face_i} has only {len(inds)} vertices")

        if face_is_weapon(face_i):
            removed_weapons += 1
        else:
            # Geometry-only canonical key removes exact duplicate surfaces even if
            # their winding or polygon start vertex differs. Keep the first face's
            # winding and material assignment.
            key = (len(inds), tuple(sorted(inds)))
            if key in seen:
                duplicate_faces += 1
            else:
                seen.add(key)
                unique_faces.append(tuple(inds))
                face_materials.append(material_id)

        face_i += 1

    if len(vertices) != SOURCE_VERTICES:
        raise RuntimeError(f"Expected {SOURCE_VERTICES} OBJ vertices, found {len(vertices)}")
    if face_i != SOURCE_FACES:
        raise RuntimeError(f"Expected {SOURCE_FACES} OBJ faces, found {face_i}")
    if removed_weapons != EXPECTED_WEAPON_FACES_REMOVED:
        raise RuntimeError(f"Expected to remove {EXPECTED_WEAPON_FACES_REMOVED} weapon faces, removed {removed_weapons}")

    used = sorted({idx for face in unique_faces for idx in face})
    remap = {old: new for new, old in enumerate(used)}
    compact_faces = [tuple(remap[i] for i in face) for face in unique_faces]

    min_x = min(v[0] for v in vertices); max_x = max(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices); max_y = max(v[1] for v in vertices)
    min_z = min(v[2] for v in vertices); max_z = max(v[2] for v in vertices)
    sx = max_x - min_x
    sy = max_y - min_y
    sz = max_z - min_z
    if min(sx, sy, sz) <= 0:
        raise RuntimeError("Invalid AKINCI source envelope")

    cx = (min_x + max_x) * 0.5
    cz = (min_z + max_z) * 0.5
    compact_vertices = []
    for old in used:
        ox, oy, oz = vertices[old]
        compact_vertices.append((
            -(ox - cx) * (TARGET_LENGTH / sx),
            (oy - min_y) * (TARGET_HEIGHT / sy),
            (oz - cz) * (TARGET_SPAN / sz),
        ))

    print(
        f"[AKINCI] source={face_i} faces; weapons_removed={removed_weapons}; "
        f"duplicates_removed={duplicate_faces}; clean={len(compact_faces)} faces / "
        f"{len(compact_vertices)} vertices"
    )

    if len(compact_faces) != EXPECTED_CLEAN_FACES:
        raise RuntimeError(
            f"Clean face count mismatch: {len(compact_faces)} vs expected {EXPECTED_CLEAN_FACES}"
        )
    if len(compact_vertices) != EXPECTED_CLEAN_VERTICES:
        raise RuntimeError(
            f"Clean vertex count mismatch: {len(compact_vertices)} vs expected {EXPECTED_CLEAN_VERTICES}"
        )

    return compact_vertices, compact_faces, face_materials


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


def build_render_mesh(vertices, faces, material_ids):
    mesh = bpy.data.meshes.new("Bayraktar_AKINCI_Static_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new("Bayraktar_AKINCI_Static", mesh)
    bpy.context.scene.collection.objects.link(obj)

    for name, rgba in zip(MATERIAL_NAMES, MATERIAL_COLORS):
        obj.data.materials.append(create_edm_material(name, rgba))

    mesh.polygons.foreach_set("material_index", array("i", material_ids))
    mesh.polygons.foreach_set("use_smooth", array("b", [1]) * len(mesh.polygons))

    obj["TPG_ORIGINAL_SOURCE_FACES"] = SOURCE_FACES
    obj["TPG_WEAPON_FACES_REMOVED"] = EXPECTED_WEAPON_FACES_REMOVED
    obj["TPG_DUPLICATE_POLYGONS_REMOVED"] = SOURCE_FACES - EXPECTED_WEAPON_FACES_REMOVED - len(faces)
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
    if len(obj.data.vertices) != EXPECTED_CLEAN_VERTICES or len(obj.data.polygons) != EXPECTED_CLEAN_FACES:
        raise RuntimeError("Final clean mesh count mismatch")
    print(f"[AKINCI] VALIDATION PASS dims={dims} verts={len(obj.data.vertices)} faces={len(obj.data.polygons)}")
    print("[AKINCI] weapons removed; empty pylons retained; duplicate source polygons collapsed")


def main():
    clear_scene()
    vertices, faces, materials = parse_and_clean_obj(reconstruct_obj_bytes())
    aircraft = build_render_mesh(vertices, faces, materials)
    add_collision_shells()
    validate(aircraft)
    bpy.context.view_layer.objects.active = aircraft
    aircraft.select_set(True)
    print("[AKINCI] scene ready for native official ED EDM export")


main()
