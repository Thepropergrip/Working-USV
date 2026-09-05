import os
from pathlib import Path
import bpy
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial

workspace = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
tex_dir = workspace / 'edm-jobs' / 'ground109_road_textures'

# Exact dimensions requested: 30 ft length. Chosen road width: 18 ft traveled way,
# plus 2.5 ft feathered shoulders each side to help hide terrain grass/clipping.
FT = 0.3048
LENGTH = 30.0 * FT
ROAD_W = 18.0 * FT
SHOULDER = 2.5 * FT
HALF_L = LENGTH / 2.0
HALF_ROAD = ROAD_W / 2.0
HALF_TOTAL = HALF_ROAD + SHOULDER

# Raised/crowned road bed. This does not truly disable DCS procedural grass;
# it physically lifts the road surface above most grass while feathering to terrain.
EDGE_Z = 0.018
ROAD_EDGE_Z = 0.135
CROWN_Z = 0.185
BASE_Z = -0.035
TEX_SCALE_M = 2.0

xs = [-HALF_TOTAL, -HALF_ROAD, 0.0, HALF_ROAD, HALF_TOTAL]
zs = [EDGE_Z, ROAD_EDGE_Z, CROWN_Z, ROAD_EDGE_Z, EDGE_Z]
ys = [-HALF_L, HALF_L]

verts = []
for y in ys:
    for x, z in zip(xs, zs):
        verts.append((x, y, z))
faces = []
for i in range(len(xs)-1):
    a=i; b=i+1; c=len(xs)+i+1; d=len(xs)+i
    faces.append((a,b,c,d))
base_start = len(verts)
for y in ys:
    verts.append((-HALF_TOTAL, y, BASE_Z))
    verts.append(( HALF_TOTAL, y, BASE_Z))
faces.append((0, len(xs), base_start+2, base_start+0))
faces.append((len(xs)-1, 2*len(xs)-1, base_start+3, base_start+1))
faces.append((base_start+0, base_start+1, 4,3,2,1,0))
faces.append((base_start+2, 5,6,7,8,9, base_start+3))
faces.append((base_start+0, base_start+2, base_start+3, base_start+1))

mesh = bpy.data.meshes.new('TPG_Ground109_Road_30ft_Mesh')
mesh.from_pydata(verts, [], faces)
mesh.update()
road = bpy.data.objects.new('TPG_GROUND109_ROAD_30FT', mesh)
bpy.context.collection.objects.link(road)

uv_layer = mesh.uv_layers.new(name='UVMap')
for poly in mesh.polygons:
    for li in poly.loop_indices:
        vi = mesh.loops[li].vertex_index
        x,y,z = mesh.vertices[vi].co
        uv_layer.data[li].uv = ((x / TEX_SCALE_M) + 0.5, (y / TEX_SCALE_M) + 0.5)

mat = bpy.data.materials.new('TPG_Ground109_Road_PBR')
mat.use_nodes = True
mat.node_tree.nodes.clear()
material_descs = build_material_descriptions()
default_desc = material_descs.get(DefaultMaterial.name)
if default_desc is None:
    raise RuntimeError('ED Default Material description could not be loaded')
edm = mat.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
edm.post_init(default_desc)
edm.name = 'EDM_Ground109_Road'
edm.label = 'Ground109 exact PBR'

def add_tex(filename, socket_name, colorspace='Non-Color'):
    path = tex_dir / filename
    if not path.exists():
        raise FileNotFoundError(path)
    img = bpy.data.images.load(str(path), check_existing=True)
    try:
        img.colorspace_settings.name = colorspace
    except Exception:
        pass
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = img
    node.label = filename
    sock = edm.inputs.get(socket_name)
    if sock is None:
        raise RuntimeError(f'Missing EDM socket: {socket_name}')
    mat.node_tree.links.new(node.outputs['Color'], sock)
    return node

# Build DCS RoughMet from the exact uploaded source pack: R=AO, G=Roughness, B=Metallic(0).
import numpy as np
ao_path = tex_dir / 'Ground109_2K-PNG_AmbientOcclusion.png'
rough_path = tex_dir / 'Ground109_2K-PNG_Roughness.png'
ao_img = bpy.data.images.load(str(ao_path), check_existing=True)
rough_img = bpy.data.images.load(str(rough_path), check_existing=True)
if tuple(ao_img.size) != tuple(rough_img.size):
    raise RuntimeError('AO/Roughness dimensions differ')
w, h = ao_img.size
ao_px = np.array(ao_img.pixels[:], dtype=np.float32).reshape((-1,4))[:,0]
rough_px = np.array(rough_img.pixels[:], dtype=np.float32).reshape((-1,4))[:,0]
out = np.empty((w*h,4), dtype=np.float32)
out[:,0] = ao_px
out[:,1] = rough_px
out[:,2] = 0.0
out[:,3] = 1.0
rm_path = tex_dir / 'TPG_Ground109_RoughMet.png'
rm_img = bpy.data.images.new('TPG_Ground109_RoughMet', width=w, height=h, alpha=True)
rm_img.colorspace_settings.name = 'Non-Color'
rm_img.pixels.foreach_set(out.ravel())
rm_img.filepath_raw = str(rm_path)
rm_img.file_format = 'PNG'
rm_img.save()

add_tex('Ground109_2K-PNG_Color.png', 'Base Color', 'sRGB')
add_tex('Ground109_2K-PNG_NormalGL.png', 'Normal (Non-Color)', 'Non-Color')
add_tex('TPG_Ground109_RoughMet.png', 'RoughMet (Non-Color)', 'Non-Color')
alpha = edm.inputs.get('Base Alpha*')
if alpha is not None:
    alpha.default_value = 1.0
road.data.materials.append(mat)
for p in mesh.polygons:
    p.use_smooth = False

# Closed collision prism follows the exact crown + shoulders, but extends deeply
# below terrain. Very thin wide DCS collision shells can be unreliable; this gives
# the shell >1 m vertical depth without changing the visible road height.
COLL_BOTTOM_Z = -1.0
n = len(xs)
cverts = []
for y in ys:
    for x, z in zip(xs, zs):
        cverts.append((x, y, z))
for y in ys:
    for x in xs:
        cverts.append((x, y, COLL_BOTTOM_Z))

cfaces = []
# Crown/shoulder top.
for i in range(n - 1):
    cfaces.append((i, i+1, n+i+1, n+i))
# Flat underside.
for i in range(n - 1):
    cfaces.append((2*n+i, 3*n+i, 3*n+i+1, 2*n+i+1))
# Long outer sides.
cfaces.append((0, n, 3*n, 2*n))
cfaces.append((n-1, 2*n-1, 4*n-1, 3*n-1))
# End caps, split across crown strips.
for i in range(n - 1):
    cfaces.append((i, 2*n+i, 2*n+i+1, i+1))
    cfaces.append((n+i, n+i+1, 3*n+i+1, 3*n+i))

cmesh = bpy.data.meshes.new('TPG_Ground109_Road_30ft_CollisionMesh')
cmesh.from_pydata(cverts, [], cfaces)
cmesh.update()
col = bpy.data.objects.new('TPG_GROUND109_ROAD_30FT_COLLISION', cmesh)
bpy.context.collection.objects.link(col)
if not hasattr(col, 'EDMProps'):
    raise RuntimeError('EDM object properties were not registered')
col.EDMProps.SPECIAL_TYPE = 'COLLISION_SHELL'

road['TPG_ASSET'] = 'Ground109 Road 30ft'
road['LENGTH_M'] = LENGTH
road['ROAD_WIDTH_M'] = ROAD_W
road['OVERALL_WIDTH_M'] = HALF_TOTAL*2
road['CROWN_HEIGHT_M'] = CROWN_Z
road['GRASS_MITIGATION'] = 'raised crowned roadbed with feathered shoulders; DCS has no per-static grass exclusion mask'
road['COLLISION_BOTTOM_Z_M'] = COLL_BOTTOM_Z

print(f'[TPG ROAD] length={LENGTH:.4f}m (30ft), road_width={ROAD_W:.4f}m (18ft), overall_width={HALF_TOTAL*2:.4f}m')
print(f'[TPG ROAD] road surface z={ROAD_EDGE_Z:.3f}-{CROWN_Z:.3f}m, edge z={EDGE_Z:.3f}m')
print('[TPG ROAD] exact source Color + NormalGL + generated AO/Roughness/Metal RoughMet linked to ED material')
print(f'[TPG ROAD] crowned collision prism follows visible road surface and extends to z={COLL_BOTTOM_Z:.3f}m')
