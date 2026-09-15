from __future__ import annotations
import base64, lzma, os
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

TARGET_HEIGHT_M = 6.0
ROOT = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
SRC_DIR = ROOT / 'cctv-build' / 'source'
TMP_DIR = ROOT / 'cctv-build' / '_runtime'
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Reconstruct the user-supplied binary FBX from repository-safe base64 chunks.
b64 = ''.join(p.read_text(encoding='ascii').strip() for p in sorted(SRC_DIR.glob('part_*.b64')))
if not b64:
    raise RuntimeError('No CCTV FBX source chunks found')
fbx_bytes = lzma.decompress(base64.b64decode(b64))
fbx_path = TMP_DIR / 'cctv_high.fbx'
fbx_path.write_bytes(fbx_bytes)
print(f'[CCTV] Reconstructed FBX: {len(fbx_bytes):,} bytes')

# Import faithfully from the source FBX.
bpy.ops.import_scene.fbx(filepath=str(fbx_path))
mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not mesh_objs:
    raise RuntimeError('FBX import produced no mesh objects')
print(f'[CCTV] Imported meshes: {len(mesh_objs)}')
print('[CCTV] Imported materials:', [m.name for m in bpy.data.materials])

# Bake every mesh into world space before rescaling/grounding so FBX hierarchy
# and object transforms cannot change the final DCS placement.
for obj in mesh_objs:
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    mw = obj.matrix_world.copy()
    for v in obj.data.vertices:
        v.co = mw @ v.co
    obj.matrix_world = Matrix.Identity(4)
    obj.parent = None

# Remove imported helpers/empties/lights/cameras after transforms are baked.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)


def bounds(objs):
    mins = Vector((1e30, 1e30, 1e30))
    maxs = Vector((-1e30, -1e30, -1e30))
    for o in objs:
        for v in o.data.vertices:
            c = v.co
            mins.x = min(mins.x, c.x); mins.y = min(mins.y, c.y); mins.z = min(mins.z, c.z)
            maxs.x = max(maxs.x, c.x); maxs.y = max(maxs.y, c.y); maxs.z = max(maxs.z, c.z)
    return mins, maxs

mn, mx = bounds(mesh_objs)
ext = mx - mn
print(f'[CCTV] Imported bounds min={tuple(round(x,4) for x in mn)} max={tuple(round(x,4) for x in mx)} ext={tuple(round(x,4) for x in ext)}')

# CCTV poles are vertically dominant. Blender's FBX importer normally resolves
# axis conversion itself; this fallback only fires if the dominant source axis
# clearly is not Z.
if ext.z < max(ext.x, ext.y) * 0.70:
    dominant = 0 if ext.x >= ext.y else 1
    print(f'[CCTV] Dominant axis is {"X" if dominant == 0 else "Y"}; remapping it to Z')
    for o in mesh_objs:
        for v in o.data.vertices:
            x, y, z = v.co
            if dominant == 0:
                v.co = (z, y, x)
            else:
                v.co = (x, z, y)
    mn, mx = bounds(mesh_objs); ext = mx - mn

if ext.z <= 0:
    raise RuntimeError('Invalid model height')
scale = TARGET_HEIGHT_M / ext.z
cx = (mn.x + mx.x) * 0.5
cy = (mn.y + mx.y) * 0.5
for o in mesh_objs:
    for v in o.data.vertices:
        v.co.x = (v.co.x - cx) * scale
        v.co.y = (v.co.y - cy) * scale
        v.co.z = (v.co.z - mn.z) * scale

mn2, mx2 = bounds(mesh_objs)
print(f'[CCTV] Final bounds min={tuple(round(x,4) for x in mn2)} max={tuple(round(x,4) for x in mx2)} height={mx2.z-mn2.z:.4f}m')

# Use ED's actual native PBR material node. The final DCS mod supplies the full
# 2K maps; tiny temporary files are only needed so the exporter can record the
# texture names in the EDM.
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial
mat_desc = build_material_descriptions()[DefaultMaterial.name]
shared_tree = None

# 1x1 opaque PNG, only for exporter bookkeeping.
PNG_1X1 = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL1WQAAAABJRU5ErkJggg==')

def temp_image(filename: str, non_color: bool):
    p = TMP_DIR / filename
    p.write_bytes(PNG_1X1)
    img = bpy.data.images.get(filename)
    if img is None:
        img = bpy.data.images.load(str(p), check_existing=False)
        img.name = filename
    img.filepath = str(p)
    try:
        img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    except Exception:
        pass
    return img


def classify_material(name: str, fallback_index: int) -> str:
    n = name.lower().replace(' ', '_')
    if 'map_one' in n or 'mapone' in n or 'map_1' in n:
        return 'Map_One'
    if 'map_two' in n or 'maptwo' in n or 'map_2' in n:
        return 'Map_Two'
    return 'Map_One' if fallback_index == 0 else 'Map_Two'

materials = list(bpy.data.materials)
for idx, mat in enumerate(materials):
    texset = classify_material(mat.name, idx)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    edm = nt.nodes.new(type=DefaultMaterial.node_group_name)
    if shared_tree is None:
        edm.post_init(mat_desc)
        shared_tree = edm.node_tree
    else:
        edm.node_tree = shared_tree
    edm.name = f'EDM_{texset}'
    try: edm.shadow_caster = 'SHADOW_CASTER_YES'
    except Exception: pass
    try: edm.transparency = 'OPAQUE'
    except Exception: pass

    def attach(filename: str, socket_name: str, non_color: bool):
        node = nt.nodes.new('ShaderNodeTexImage')
        node.name = filename
        node.label = filename
        node.image = temp_image(filename, non_color)
        nt.links.new(node.outputs['Color'], edm.inputs[socket_name])

    attach(f'{texset}_BaseColor.png', 'Base Color', False)
    attach(f'{texset}_RoughMet.png', 'RoughMet (Non-Color)', True)
    attach(f'{texset}_Normal.png', 'Normal (Non-Color)', True)
    print(f'[CCTV] Material {mat.name!r} -> {texset}')

# Triangulate the render geometry non-destructively at mesh-data level for a
# deterministic game mesh while retaining original normals/UVs/material slots.
for obj in mesh_objs:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new(name='TPG_Triangulate', type='TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)

# Lightweight DCS collision: pole + upper equipment envelope. These are special
# COLLISION_SHELL nodes and do not render.
def make_collision_box(name, dims, center):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.EDMProps.SPECIAL_TYPE = 'COLLISION_SHELL'
    return o

def make_collision_cylinder(name, radius, depth, z):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=depth, location=(0,0,z))
    o = bpy.context.object
    o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.EDMProps.SPECIAL_TYPE = 'COLLISION_SHELL'
    return o

# Pole diameter deliberately modest; top box covers camera/control hardware.
make_collision_cylinder('TPG_CCTV_COLLISION_POLE', 0.18, 5.35, 2.675)
upper_w = max(0.8, min(2.4, (mx2.x - mn2.x) * 0.95))
upper_d = max(0.8, min(2.4, (mx2.y - mn2.y) * 0.95))
make_collision_box('TPG_CCTV_COLLISION_HEAD', (upper_w, upper_d, 0.75), (0,0,5.55))

# Stable names improve debugging in ModelViewer/DCS logs.
for i, obj in enumerate(mesh_objs, 1):
    obj.name = f'TPG_CCTV_VIS_{i:03d}'

print('[CCTV] Build prepared for native EDM export')
