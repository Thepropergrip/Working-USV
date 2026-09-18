from __future__ import annotations

import base64
import lzma
import struct
from array import array
from pathlib import Path

import bpy

# -----------------------------------------------------------------------------
# TPG Bayraktar AKINCI static-aircraft EDM build
# Source payload: exact uploaded PLY, losslessly XZ-compressed and split as
# base64 text parts for GitHub transport. Face-order deletion ranges were
# derived byte-for-byte against the user's cleaned OBJ: weapons removed while
# the empty pylon/rack geometry remains.
# -----------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "assets" / "akinci" / "source"
PART_GLOB = "part*.b64"
TMP_PLY = ROOT / "assets" / "akinci" / "_reconstructed_source.ply"

EXPECTED_VERTICES = 51691
EXPECTED_FACES = 711608
TARGET_LENGTH = 12.3
TARGET_HEIGHT = 4.1
TARGET_SPAN = 20.0

REMOVE_FACE_RANGES = (
    (225250, 233827),
    (238446, 254673),
    (281962, 281967),
    (711413, 711604),
)

MATERIAL_BLOCKS = (
    (0, 55587, "Metal_Paint"),
    (55588, 234417, "asdkk"),
    (234418, 254673, "Metal_Paint.004"),
    (254674, 254825, "Metal_Paint.003"),
    (254826, 281967, "chrome"),
    (281968, 302703, "white"),
    (302704, 327279, "Air_Duct_Rubber.001"),
    (327280, 406511, "Steel.002"),
    (406512, 408431, "Metal_Paint.001"),
    (408432, 412237, "Material_001"),
    (412238, 412749, "idgu_002"),
    (412750, 412751, "Smuged_Glass"),
    (412752, 415855, "Material_002"),
    (415856, 593007, "Steel"),
    (593008, 661103, "Steel.001"),
    (661104, 710255, "Air_Duct_Rubber"),
    (710256, 711412, "idgu_001"),
    (711413, 711604, "idgu"),
    (711605, 711606, "Glass_dark"),
    (711607, 711607, "Material_007"),
)

MATERIAL_STYLE = {
    "Metal_Paint":          ((0.62, 0.64, 0.64, 1.0), False),
    "asdkk":                ((0.18, 0.19, 0.19, 1.0), False),
    "Metal_Paint.004":      ((0.68, 0.69, 0.69, 1.0), False),
    "Metal_Paint.003":      ((0.42, 0.44, 0.44, 1.0), False),
    "chrome":               ((0.65, 0.67, 0.68, 1.0), False),
    "white":                ((0.92, 0.92, 0.90, 1.0), False),
    "Air_Duct_Rubber.001":  ((0.025, 0.028, 0.030, 1.0), False),
    "Steel.002":            ((0.34, 0.36, 0.37, 1.0), False),
    "Metal_Paint.001":      ((0.58, 0.60, 0.60, 1.0), False),
    "Material_001":         ((0.20, 0.21, 0.22, 1.0), False),
    "idgu_002":             ((0.12, 0.13, 0.14, 1.0), False),
    "Smuged_Glass":         ((0.08, 0.11, 0.13, 1.0), True),
    "Material_002":         ((0.25, 0.26, 0.27, 1.0), False),
    "Steel":                ((0.32, 0.34, 0.35, 1.0), False),
    "Steel.001":            ((0.30, 0.32, 0.33, 1.0), False),
    "Air_Duct_Rubber":      ((0.025, 0.028, 0.030, 1.0), False),
    "idgu_001":             ((0.15, 0.16, 0.17, 1.0), False),
    "idgu":                 ((0.20, 0.21, 0.22, 1.0), False),
    "Glass_dark":           ((0.04, 0.06, 0.08, 1.0), True),
    "Material_007":         ((0.22, 0.23, 0.24, 1.0), False),
}

def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

def reconstruct_source() -> Path:
    parts = sorted(SOURCE_DIR.glob(PART_GLOB))
    if not parts:
        raise FileNotFoundError(f"No source payload parts found in {SOURCE_DIR}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    packed = base64.b64decode(encoded, validate=True)
    raw = lzma.decompress(packed)
    TMP_PLY.write_bytes(raw)
    print(f"[AKINCI] Reconstructed PLY: {TMP_PLY} ({len(raw)} bytes, {len(parts)} parts)")
    return TMP_PLY

def is_removed(face_index: int) -> bool:
    for lo, hi in REMOVE_FACE_RANGES:
        if lo <= face_index <= hi:
            return True
    return False

def material_name_for_face(face_index: int) -> str:
    for lo, hi, name in MATERIAL_BLOCKS:
        if lo <= face_index <= hi:
            return name
    raise RuntimeError(f"No material block for original face {face_index}")

def parse_binary_ply(path: Path):
    data = path.read_bytes()
    marker = b"end_header\n"
    h_end = data.find(marker)
    marker_len = len(marker)
    if h_end < 0:
        marker = b"end_header\r\n"
        h_end = data.find(marker)
        marker_len = len(marker)
    if h_end < 0:
        raise RuntimeError("PLY end_header not found")
    header = data[:h_end + marker_len].decode("ascii", errors="strict")
    if "format binary_little_endian 1.0" not in header:
        raise RuntimeError("Expected binary little-endian PLY")
    v_count = f_count = None
    for line in header.splitlines():
        if line.startswith("element vertex "):
            v_count = int(line.split()[-1])
        elif line.startswith("element face "):
            f_count = int(line.split()[-1])
    if v_count != EXPECTED_VERTICES or f_count != EXPECTED_FACES:
        raise RuntimeError(f"Unexpected PLY counts: vertices={v_count}, faces={f_count}")
    off = h_end + marker_len
    v_struct = struct.Struct("<8f")
    vertices = []
    normals = []
    uvs = []
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    for _ in range(v_count):
        x, y, z, nx, ny, nz, s, t = v_struct.unpack_from(data, off)
        off += v_struct.size
        vertices.append([x, y, z])
        normals.append((nx, ny, nz))
        uvs.append((s, t))
        min_x = min(min_x, x); max_x = max(max_x, x)
        min_y = min(min_y, y); max_y = max(max_y, y)
        min_z = min(min_z, z); max_z = max(max_z, z)
    sx = max_x - min_x
    sy = max_y - min_y
    sz = max_z - min_z
    cx = (min_x + max_x) * 0.5
    cz = (min_z + max_z) * 0.5
    for v in vertices:
        ox, oy, oz = v
        v[0] = -(ox - cx) * (TARGET_LENGTH / sx)
        v[1] = (oy - min_y) * (TARGET_HEIGHT / sy)
        v[2] = (oz - cz) * (TARGET_SPAN / sz)
    nsx = -(TARGET_LENGTH / sx)
    nsy = TARGET_HEIGHT / sy
    nsz = TARGET_SPAN / sz
    corrected_normals = []
    for nx, ny, nz in normals:
        tx = nx / nsx
        ty = ny / nsy
        tz = nz / nsz
        mag = (tx*tx + ty*ty + tz*tz) ** 0.5
        if mag > 1e-12:
            corrected_normals.append((tx/mag, ty/mag, tz/mag))
        else:
            corrected_normals.append((0.0, 1.0, 0.0))
    faces = []
    mat_names = []
    for fi in range(f_count):
        n = data[off]
        off += 1
        if n < 3 or n > 64:
            raise RuntimeError(f"Invalid PLY face vertex count {n} at face {fi}")
        fmt = struct.Struct("<" + "I" * n)
        inds = fmt.unpack_from(data, off)
        off += fmt.size
        if not is_removed(fi):
            faces.append(inds)
            mat_names.append(material_name_for_face(fi))
    if len(faces) != 686604:
        raise RuntimeError(f"Expected 686604 faces after weapon removal, got {len(faces)}")
    print(f"[AKINCI] Source: {v_count} verts / {f_count} faces; kept {len(faces)}, removed {f_count-len(faces)} weapon faces")
    print(f"[AKINCI] Target envelope: {TARGET_LENGTH:.3f}m L x {TARGET_SPAN:.3f}m span x {TARGET_HEIGHT:.3f}m H")
    return vertices, corrected_normals, uvs, faces, mat_names

def create_edm_material(name: str, rgba, glass_hint: bool = False):
    from materials.materials import build_material_descriptions
    from materials.material_default import DefaultMaterial
    descs = build_material_descriptions()
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = rgba
    nt = mat.node_tree
    nt.nodes.clear()
    node = nt.nodes.new(type=DefaultMaterial.node_group_name)
    node.post_init(descs[DefaultMaterial.name])
    base = node.inputs.get("Base Color")
    if base is not None:
        base.default_value = rgba
    alpha = node.inputs.get("Base Alpha*")
    if alpha is not None:
        alpha.default_value = 1.0
    if glass_hint:
        opacity = node.inputs.get("Opacity Value")
        if opacity is not None:
            opacity.default_value = 1.0
    return mat

def build_render_mesh(vertices, normals, uvs, faces, face_mat_names):
    mesh = bpy.data.meshes.new("Bayraktar_AKINCI_Static_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new("Bayraktar_AKINCI_Static", mesh)
    bpy.context.collection.objects.link(obj)
    unique_names = []
    for _, _, name in MATERIAL_BLOCKS:
        if name not in unique_names:
            unique_names.append(name)
    mat_index = {}
    for name in unique_names:
        rgba, glass_hint = MATERIAL_STYLE[name]
        mat = create_edm_material(name, rgba, glass_hint)
        obj.data.materials.append(mat)
        mat_index[name] = len(obj.data.materials) - 1
    poly_mats = array('i', (mat_index[n] for n in face_mat_names))
    mesh.polygons.foreach_set("material_index", poly_mats)
    for p in mesh.polygons:
        p.use_smooth = True
    try:
        mesh.normals_split_custom_set_from_vertices(normals)
    except Exception as exc:
        print(f"[AKINCI] Custom vertex normals not applied ({exc}); Blender-calculated smooth normals will be used")
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_flat = array('f')
    for loop in mesh.loops:
        u, v = uvs[loop.vertex_index]
        uv_flat.extend((u, v))
    uv_layer.data.foreach_set("uv", uv_flat)
    obj["TPG_SOURCE_FACES"] = EXPECTED_FACES
    obj["TPG_WEAPON_FACES_REMOVED"] = EXPECTED_FACES - len(faces)
    obj["TPG_EMPTY_PYLONS_RETAINED"] = True
    return obj

def add_collision_box(name, center, dims):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.EDMProps.SPECIAL_TYPE = 'COLLISION_SHELL'
    return obj

def add_collision_shells():
    add_collision_box("COLLISION_Fuselage", (0.35, 1.58, 0.0), (10.8, 2.25, 1.75))
    add_collision_box("COLLISION_Wing", (0.35, 2.30, 0.0), (3.35, 0.38, 18.7))
    add_collision_box("COLLISION_Tail", (-4.85, 2.55, 0.0), (2.0, 1.25, 6.2))

def validate(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    dims = (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    expect = (TARGET_LENGTH, TARGET_HEIGHT, TARGET_SPAN)
    for got, exp in zip(dims, expect):
        if abs(got-exp) > 0.002:
            raise RuntimeError(f"Envelope validation failed: got {dims}, expected {expect}")
    if len(obj.data.polygons) != 686604:
        raise RuntimeError(f"Face-count validation failed: {len(obj.data.polygons)}")
    print(f"[AKINCI] VALIDATION PASS: dims={dims}, faces={len(obj.data.polygons)}, pylons retained / weapons removed")

def main():
    clear_scene()
    src = reconstruct_source()
    vertices, normals, uvs, faces, mat_names = parse_binary_ply(src)
    obj = build_render_mesh(vertices, normals, uvs, faces, mat_names)
    add_collision_shells()
    validate(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    print("[AKINCI] Build complete; handing scene to official ED EDM exporter")

main()
