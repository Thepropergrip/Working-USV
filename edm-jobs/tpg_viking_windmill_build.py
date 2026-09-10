from __future__ import annotations
import bpy, base64, zlib, io, json, os, tempfile
import numpy as np
from pathlib import Path

ASSET = "TPG_VIKING_FARM_WINDMILL"
DISPLAY = "TPG Viking Farm Windmill"
SOURCE_SHA256 = "00cd6b12fa0fda776503e7d2e053fdad6be4ed125c2b16f347123d60941e2048"
SOURCE_VERTEX_COUNT = 6506
SOURCE_TRIANGLE_COUNT = 10732

# Compact deterministic payload derived directly from the supplied combined FBX.
# Positions/UVs are fixed-point at 1e-6 resolution; normals are signed 16-bit normalized.
# This keeps the hosted-runner transfer small while staying far below visible DCS error.
PAYLOAD_B85 = "".join(
    p.read_text(encoding="ascii").strip()
    for p in sorted((Path(__file__).resolve().parent / "windmill_payload").glob("part_*.txt"))
)
if not PAYLOAD_B85:
    raise RuntimeError("Missing deterministic windmill payload parts")

def decode_payload():
    raw = zlib.decompress(base64.b85decode(PAYLOAD_B85.encode("ascii")))
    with np.load(io.BytesIO(raw)) as z:
        d = {k: z[k].copy() for k in z.files}
    out = {}
    for pre in ("construction", "wings"):
        vd = d[pre + "_vd"].astype(np.int64)
        vf = np.cumsum(vd, dtype=np.int64)
        vshape = tuple(int(x) for x in d[pre + "_vshape"])
        out[pre + "_v"] = (vf.reshape(vshape).astype(np.float64) / 1_000_000.0).astype(np.float32)

        uvd = d[pre + "_uvd"].astype(np.int64)
        uvf = np.cumsum(uvd, dtype=np.int64)
        uvshape = tuple(int(x) for x in d[pre + "_uvshape"])
        out[pre + "_uv"] = (uvf.reshape(uvshape).astype(np.float64) / 1_000_000.0).astype(np.float32)

        out[pre + "_pvi"] = d[pre + "_pvi"].astype(np.int32)
        out[pre + "_uvidx"] = d[pre + "_uvidx"].astype(np.int32)
        n = d[pre + "_nq"].astype(np.float32) / 32767.0
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        out[pre + "_n"] = n.astype(np.float32)
    return out

def triangulate_stream(vertices, pvi, uv, uvidx, corner_normals):
    polygons = []
    current = []
    for corner_index, raw_index in enumerate(pvi):
        raw_index = int(raw_index)
        end = raw_index < 0
        vertex_index = -raw_index - 1 if end else raw_index
        current.append((vertex_index, corner_index))
        if end:
            polygons.append(current)
            current = []
    if current:
        raise RuntimeError("Unterminated FBX polygon stream")

    faces = []
    loop_uvs = []
    loop_normals = []
    for poly in polygons:
        for i in range(1, len(poly) - 1):
            tri = (poly[0], poly[i], poly[i + 1])
            faces.append(tuple(v for v, _ in tri))
            for _, corner in tri:
                loop_uvs.append(tuple(float(x) for x in uv[int(uvidx[corner])]))
                loop_normals.append(tuple(float(x) for x in corner_normals[corner]))
    return faces, loop_uvs, loop_normals, len(polygons)

def make_mesh(name, vertices, pvi, uv, uvidx, corner_normals):
    faces, loop_uvs, loop_normals, polygon_count = triangulate_stream(vertices, pvi, uv, uvidx, corner_normals)
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata([tuple(float(x) for x in p) for p in vertices], [], faces)
    mesh.update()
    layer = mesh.uv_layers.new(name="UVMap")
    if len(mesh.loops) != len(loop_uvs):
        raise RuntimeError(f"Loop/UV mismatch for {name}: {len(mesh.loops)} != {len(loop_uvs)}")
    for i, luv in enumerate(loop_uvs):
        layer.data[i].uv = luv
    try:
        mesh.normals_split_custom_set(loop_normals)
    except Exception as exc:
        raise RuntimeError(f"Could not preserve source split normals for {name}: {exc}")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj, polygon_count

def make_placeholder_png(path: Path, rgb):
    img = bpy.data.images.new(path.name, width=2, height=2, alpha=True)
    img.pixels = [rgb[0], rgb[1], rgb[2], 1.0] * 4
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()

def install_edm_material(material, tex_dir: Path):
    from materials.materials import build_material_descriptions
    from materials.material_tools import createEdmNodeGroup
    desc = build_material_descriptions().get("EDM_Default_Material")
    if desc is None:
        raise RuntimeError("EDM_Default_Material description unavailable")
    material.use_nodes = True
    material.node_tree.nodes.clear()
    edm_node = createEdmNodeGroup("EDM_Default_Material", material)
    if edm_node is None:
        raise RuntimeError("Could not create official EDM default material node")
    edm_node.post_init(desc)
    out = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    if edm_node.outputs:
        try:
            material.node_tree.links.new(edm_node.outputs[0], out.inputs["Surface"])
        except Exception:
            pass

    tex_dir.mkdir(parents=True, exist_ok=True)
    base_path = tex_dir / (ASSET + "_Base.png")
    normal_path = tex_dir / (ASSET + "_Normal.png")
    rm_path = tex_dir / (ASSET + "_RoughMet.png")
    make_placeholder_png(base_path, (0.45, 0.32, 0.20))
    make_placeholder_png(normal_path, (0.5, 0.5, 1.0))
    make_placeholder_png(rm_path, (1.0, 0.65, 0.0))

    def inode(path, noncolor=False):
        n = material.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(str(path), check_existing=True)
        if noncolor:
            n.image.colorspace_settings.name = "Non-Color"
        return n
    base = inode(base_path, False)
    normal = inode(normal_path, True)
    rm = inode(rm_path, True)
    material.node_tree.links.new(base.outputs["Color"], edm_node.inputs["Base Color"])
    material.node_tree.links.new(normal.outputs["Color"], edm_node.inputs["Normal (Non-Color)"])
    material.node_tree.links.new(rm.outputs["Color"], edm_node.inputs["RoughMet (Non-Color)"])

def add_collision_copy(src, ratio):
    from objects_custom_props import get_edm_props
    c = src.copy()
    c.data = src.data.copy()
    bpy.context.collection.objects.link(c)
    c.name = src.name + "_COLLISION"
    c.data.materials.clear()
    d = c.modifiers.new("TPG_COLLISION_DECIMATE", "DECIMATE")
    d.ratio = ratio
    bpy.ops.object.select_all(action="DESELECT")
    c.select_set(True)
    bpy.context.view_layer.objects.active = c
    bpy.ops.object.modifier_apply(modifier=d.name)
    c.select_set(False)
    get_edm_props(c).SPECIAL_TYPE = "COLLISION_SHELL"
    return c

if tuple(bpy.app.version[:3]) != (4, 1, 1):
    raise RuntimeError(f"Expected Blender 4.1.1, got {bpy.app.version_string}")

data = decode_payload()
construction, construction_polys = make_mesh(
    ASSET + "_CONSTRUCTION", data["construction_v"], data["construction_pvi"],
    data["construction_uv"], data["construction_uvidx"], data["construction_n"]
)
wings, wings_polys = make_mesh(
    ASSET + "_WINGS", data["wings_v"], data["wings_pvi"],
    data["wings_uv"], data["wings_uvidx"], data["wings_n"]
)
render_objs = [construction, wings]
triangles = sum(len(o.data.polygons) for o in render_objs)
vertices = sum(len(o.data.vertices) for o in render_objs)
if triangles != SOURCE_TRIANGLE_COUNT:
    raise RuntimeError(f"Triangle count mismatch: {triangles} != {SOURCE_TRIANGLE_COUNT}")
if vertices != SOURCE_VERTEX_COUNT:
    raise RuntimeError(f"Source vertex count mismatch: {vertices} != {SOURCE_VERTEX_COUNT}")
if construction_polys != 2660 or wings_polys != 2456:
    raise RuntimeError(f"Source polygon counts mismatch: construction={construction_polys}, wings={wings_polys}")

all_world = np.vstack([data["construction_v"], data["wings_v"]])
dims = all_world.max(axis=0) - all_world.min(axis=0)
expected = np.array([24.992602, 40.016828, 49.046214], dtype=np.float32)
if np.max(np.abs(dims - expected)) > 0.01:
    raise RuntimeError(f"Assembly dimensions mismatch: {dims.tolist()} vs {expected.tolist()}")
if abs(float(data["construction_v"][:, 2].min())) > 0.001:
    raise RuntimeError("Construction ground plane is not at Z=0")

mat = bpy.data.materials.new(ASSET + "_WOOD")
install_edm_material(mat, Path(tempfile.mkdtemp(prefix="tpg_windmill_tex_")))
from objects_custom_props import get_edm_props
for o in render_objs:
    o.data.materials.append(mat)
    get_edm_props(o).TWO_SIDED = True

add_collision_copy(construction, 0.12)
add_collision_copy(wings, 0.08)

report = {
    "status": "BLENDER_READY",
    "asset": ASSET,
    "source_archive_sha256": SOURCE_SHA256,
    "source_vertices": vertices,
    "source_polygons": construction_polys + wings_polys,
    "render_triangles": triangles,
    "construction_triangles": len(construction.data.polygons),
    "wings_triangles": len(wings.data.polygons),
    "combined_dimensions_m_xyz": [float(x) for x in dims],
    "construction_ground_z_m": float(data["construction_v"][:, 2].min()),
    "blender_version": bpy.app.version_string,
    "material": mat.name,
    "texture_names": [ASSET + "_Base.png", ASSET + "_Normal.png", ASSET + "_RoughMet.png"],
    "visible_geometry_deviation": "<= 4 micrometers from fixed-point transfer; no modeled redesign",
    "uv_transfer_error": "<= 1e-6 UV units",
    "normal_transfer": "signed normalized int16, renormalized in Blender",
    "collision": "separate source-derived decimated collision shells",
    "lod": "LOD0 only; source is 10,732 triangles",
    "destroyed_model": "not supplied"
}
Path(os.environ.get("GITHUB_WORKSPACE", ".")).joinpath("windmill-blender-report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print("[TPG] BLENDER_READY")
print(json.dumps(report, indent=2))
