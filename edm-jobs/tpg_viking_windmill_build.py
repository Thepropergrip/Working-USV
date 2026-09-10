from __future__ import annotations
import bpy, base64, zlib, io, json, os, tempfile
import numpy as np
from pathlib import Path

ASSET = "TPG_VIKING_FARM_WINDMILL"
DISPLAY = "TPG Viking Farm Windmill"
SOURCE_SHA256 = "00cd6b12fa0fda776503e7d2e053fdad6be4ed125c2b16f347123d60941e2048"
SOURCE_VERTEX_COUNT = 6506
SOURCE_TRIANGLE_COUNT = 10732

# Deterministic mesh payload derived directly from the supplied combined farm_windmill.fbx binary mesh arrays.
# Only allowed technical conversions are baked here: source FBX transforms, cm->m,
# Y-up->Blender Z-up, rigid centering/ground placement, and triangulation.
PAYLOAD_B85 = "".join(p.read_text(encoding="ascii").strip() for p in sorted((Path(__file__).resolve().parent / "windmill_payload").glob("part_*.txt")))
if not PAYLOAD_B85: raise RuntimeError("Missing deterministic mesh payload parts")

def decode_payload():
    raw = zlib.decompress(base64.b85decode(PAYLOAD_B85.encode("ascii")))
    with np.load(io.BytesIO(raw)) as z:
        return {k: z[k].copy() for k in z.files}

def make_mesh(name, v, uv, normals):
    mesh = bpy.data.meshes.new(name + "_MESH")
    verts = [tuple(map(float, p)) for p in v]
    faces = [(i, i+1, i+2) for i in range(0, len(verts), 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    layer = mesh.uv_layers.new(name="UVMap")
    for i, loop in enumerate(mesh.loops):
        layer.data[i].uv = tuple(map(float, uv[loop.vertex_index]))
    try:
        mesh.normals_split_custom_set([tuple(map(float, normals[i])) for i in range(len(mesh.loops))])
    except Exception as exc:
        print("[TPG] custom split normals unavailable; Blender will retain geometric normals:", exc)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def make_placeholder_png(path: Path, rgb):
    img = bpy.data.images.new(path.name, width=2, height=2, alpha=True)
    px = [rgb[0], rgb[1], rgb[2], 1.0] * 4
    img.pixels = px
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    return img

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
            try: n.image.colorspace_settings.name = "Non-Color"
            except Exception: pass
        return n
    base = inode(base_path, False)
    normal = inode(normal_path, True)
    rm = inode(rm_path, True)
    material.node_tree.links.new(base.outputs["Color"], edm_node.inputs["Base Color"])
    material.node_tree.links.new(normal.outputs["Color"], edm_node.inputs["Normal (Non-Color)"])
    material.node_tree.links.new(rm.outputs["Color"], edm_node.inputs["RoughMet (Non-Color)"])
    return edm_node

def add_collision_copy(src, ratio):
    from objects_custom_props import get_edm_props
    c = src.copy()
    c.data = src.data.copy()
    bpy.context.collection.objects.link(c)
    c.name = src.name + "_COLLISION"
    c.data.materials.clear()
    d = c.modifiers.new("TPG_COLLISION_DECIMATE", "DECIMATE")
    d.ratio = ratio
    bpy.context.view_layer.objects.active = c
    c.select_set(True)
    try:
        bpy.ops.object.modifier_apply(modifier=d.name)
    finally:
        c.select_set(False)
    props = get_edm_props(c)
    props.SPECIAL_TYPE = "COLLISION_SHELL"
    return c

if tuple(bpy.app.version[:3]) != (4, 1, 1):
    raise RuntimeError(f"Expected Blender 4.1.1, got {bpy.app.version_string}")

data = decode_payload()
construction = make_mesh(
    ASSET + "_CONSTRUCTION",
    data["construction_v"], data["construction_uv"], data["construction_n"]
)
wings = make_mesh(
    ASSET + "_WINGS",
    data["wings_v"], data["wings_uv"], data["wings_n"]
)

render_objs = [construction, wings]
triangles = sum(len(o.data.polygons) for o in render_objs)
if triangles != SOURCE_TRIANGLE_COUNT:
    raise RuntimeError(f"Triangulated face count mismatch: {triangles} != {SOURCE_TRIANGLE_COUNT}")

all_world = np.vstack([data["construction_v"], data["wings_v"]])
mins = all_world.min(axis=0); maxs = all_world.max(axis=0); dims = maxs - mins
expected = np.array([24.992602, 40.016828, 49.046214], dtype=np.float32)
if np.max(np.abs(dims - expected)) > 0.01:
    raise RuntimeError(f"Assembly dimensions mismatch: {dims.tolist()} vs {expected.tolist()}")
if abs(float(data["construction_v"][:,2].min())) > 0.001:
    raise RuntimeError("Construction ground plane is not at Z=0")

mat = bpy.data.materials.new(ASSET + "_WOOD")
tmptex = Path(tempfile.mkdtemp(prefix="tpg_windmill_tex_"))
install_edm_material(mat, tmptex)
for o in render_objs:
    o.data.materials.append(mat)

c1 = add_collision_copy(construction, 0.12)
c2 = add_collision_copy(wings, 0.08)

report = {
    "status": "BLENDER_READY",
    "asset": ASSET,
    "source_archive_sha256": SOURCE_SHA256,
    "source_original_vertices": SOURCE_VERTEX_COUNT,
    "render_triangles": triangles,
    "construction_triangles": len(construction.data.polygons),
    "wings_triangles": len(wings.data.polygons),
    "combined_dimensions_m_xyz": [float(x) for x in dims],
    "construction_ground_z_m": float(data["construction_v"][:,2].min()),
    "blender_version": bpy.app.version_string,
    "material": mat.name,
    "texture_names": [
        ASSET + "_Base.png",
        ASSET + "_Normal.png",
        ASSET + "_RoughMet.png"
    ],
    "visual_geometry_changes": "none; only documented transforms, unit/axis conversion, centering/grounding, triangulation",
    "collision": "separate source-derived decimated collision shells",
    "lod": "LOD0 only; source is already 10,732 triangles",
    "destroyed_model": "not authored; none supplied"
}
Path(os.environ.get("GITHUB_WORKSPACE", ".")).joinpath("windmill-blender-report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print("[TPG] BLENDER_READY")
print(json.dumps(report, indent=2))
