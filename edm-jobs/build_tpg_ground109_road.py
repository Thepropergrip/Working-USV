import os
from pathlib import Path
import bpy
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial

workspace = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
tex_dir = workspace / 'edm-jobs' / 'ground109_road_textures'

# TPG Ground109 single-lane road.
# User requirement: visibly LONG/NARROW, not a near-square pad.
# Exact visible footprint: 30.000 ft long x 9.000 ft overall.
# The center 8 ft is the traveled lane; 0.5 ft on each side feathers to terrain.
FT = 0.3048
LENGTH = 30.0 * FT
TRAVEL_W = 8.0 * FT
FEATHER = 0.5 * FT
OVERALL_W = TRAVEL_W + 2.0 * FEATHER
HALF_L = LENGTH / 2.0
HALF_TRAVEL = TRAVEL_W / 2.0
HALF_TOTAL = OVERALL_W / 2.0

# Longitudinal entry ramps: both head-on ends meet terrain, then rise gently.
# This is a road surface, not a textured box. No visible vertical faces are created.
RAMP_LEN = 4.0 * FT
TERRAIN_Z = 0.010
ROAD_EDGE_Z = 0.085
CROWN_Z = 0.120
COLL_BOTTOM_Z = -1.0
TEX_SCALE_M = 2.0

# Across-road profile: half-foot feather -> traveled edge -> subtle crown -> edge -> feather.
xs = [-HALF_TOTAL, -HALF_TRAVEL, 0.0, HALF_TRAVEL, HALF_TOTAL]
full_profile_z = [TERRAIN_Z, ROAD_EDGE_Z, CROWN_Z, ROAD_EDGE_Z, TERRAIN_Z]

# Along-road stations. The first/last 4 ft are two-stage drive-on ramps.
ys = [
    -HALF_L,
    -HALF_L + RAMP_LEN * 0.5,
    -HALF_L + RAMP_LEN,
     HALF_L - RAMP_LEN,
     HALF_L - RAMP_LEN * 0.5,
     HALF_L,
]
blend = [0.0, 0.5, 1.0, 1.0, 0.5, 0.0]

# -----------------------------------------------------------------------------
# VISIBLE ROAD MESH
# Top surface ONLY, intentionally matching the common DCS street-mod pattern:
# one rendered road surface and one separate collision shell. There are no
# textured vertical side/end polygons, so the Ground109 graphics cannot stretch
# down an end wall.
# -----------------------------------------------------------------------------
verts = []
for y, t in zip(ys, blend):
    for x, z_full in zip(xs, full_profile_z):
        z = TERRAIN_Z + t * (z_full - TERRAIN_Z)
        verts.append((x, y, z))

nx = len(xs)
ny = len(ys)
faces = []
for j in range(ny - 1):
    row0 = j * nx
    row1 = (j + 1) * nx
    for i in range(nx - 1):
        faces.append((row0 + i, row0 + i + 1, row1 + i + 1, row1 + i))

mesh = bpy.data.meshes.new('TPG_Ground109_Road_30ft_SingleLane_Mesh')
mesh.from_pydata(verts, [], faces)
mesh.update()
road = bpy.data.objects.new('TPG_GROUND109_ROAD_30FT_SINGLELANE', mesh)
bpy.context.collection.objects.link(road)

# World-planar UV mapping. X and Y use the SAME meters-per-tile scale, preserving
# the exact source texture proportions over the crown and entry ramps.
uv_layer = mesh.uv_layers.new(name='UVMap')
for poly in mesh.polygons:
    for li in poly.loop_indices:
        vi = mesh.loops[li].vertex_index
        x, y, z = mesh.vertices[vi].co
        uv_layer.data[li].uv = ((x / TEX_SCALE_M) + 0.5, (y / TEX_SCALE_M) + 0.5)

# -----------------------------------------------------------------------------
# ED native PBR material using the exact Ground109 maps.
# -----------------------------------------------------------------------------
mat = bpy.data.materials.new('TPG_Ground109_SingleLane_PBR')
mat.use_nodes = True
mat.node_tree.nodes.clear()
material_descs = build_material_descriptions()
default_desc = material_descs.get(DefaultMaterial.name)
if default_desc is None:
    raise RuntimeError('ED Default Material description could not be loaded')
edm = mat.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
edm.post_init(default_desc)
edm.name = 'EDM_Ground109_SingleLane'
edm.label = 'Ground109 exact PBR - single lane'

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

# DCS RoughMet from exact uploaded/source pack: R=AO, G=Roughness, B=Metallic(0).
import numpy as np
ao_path = tex_dir / 'Ground109_2K-PNG_AmbientOcclusion.png'
rough_path = tex_dir / 'Ground109_2K-PNG_Roughness.png'
ao_img = bpy.data.images.load(str(ao_path), check_existing=True)
rough_img = bpy.data.images.load(str(rough_path), check_existing=True)
if tuple(ao_img.size) != tuple(rough_img.size):
    raise RuntimeError('AO/Roughness dimensions differ')
w, h = ao_img.size
ao_px = np.array(ao_img.pixels[:], dtype=np.float32).reshape((-1, 4))[:, 0]
rough_px = np.array(rough_img.pixels[:], dtype=np.float32).reshape((-1, 4))[:, 0]
out = np.empty((w * h, 4), dtype=np.float32)
out[:, 0] = ao_px
out[:, 1] = rough_px
out[:, 2] = 0.0
out[:, 3] = 1.0
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

# -----------------------------------------------------------------------------
# COLLISION SHELL
# Separate shell, same top road profile, buried lower body. This mirrors the
# attached asphalt-street model's render-mesh + shell-node concept while keeping
# the visible model top-only.
# -----------------------------------------------------------------------------
cverts = list(verts)
for y in ys:
    for x in xs:
        cverts.append((x, y, COLL_BOTTOM_Z))

TOP_COUNT = nx * ny
cfaces = []
# Contact/top surface.
for j in range(ny - 1):
    row0 = j * nx
    row1 = (j + 1) * nx
    for i in range(nx - 1):
        cfaces.append((row0 + i, row0 + i + 1, row1 + i + 1, row1 + i))
# Buried bottom.
for j in range(ny - 1):
    row0 = TOP_COUNT + j * nx
    row1 = TOP_COUNT + (j + 1) * nx
    for i in range(nx - 1):
        cfaces.append((row0 + i, row1 + i, row1 + i + 1, row0 + i + 1))
# Buried long sides.
for j in range(ny - 1):
    t0 = j * nx
    t1 = (j + 1) * nx
    b0 = TOP_COUNT + j * nx
    b1 = TOP_COUNT + (j + 1) * nx
    cfaces.append((t0, t1, b1, b0))
    cfaces.append((t0 + nx - 1, b0 + nx - 1, b1 + nx - 1, t1 + nx - 1))
# Buried end walls. Their TOP edge is at TERRAIN_Z, so no wall protrudes at either approach.
for i in range(nx - 1):
    cfaces.append((i, TOP_COUNT + i, TOP_COUNT + i + 1, i + 1))
    top_last = (ny - 1) * nx
    bot_last = TOP_COUNT + (ny - 1) * nx
    cfaces.append((top_last + i, top_last + i + 1, bot_last + i + 1, bot_last + i))

cmesh = bpy.data.meshes.new('TPG_Ground109_Road_30ft_SingleLane_CollisionMesh')
cmesh.from_pydata(cverts, [], cfaces)
cmesh.update()
col = bpy.data.objects.new('TPG_GROUND109_ROAD_30FT_SINGLELANE_COLLISION', cmesh)
bpy.context.collection.objects.link(col)
if not hasattr(col, 'EDMProps'):
    raise RuntimeError('EDM object properties were not registered')
col.EDMProps.SPECIAL_TYPE = 'COLLISION_SHELL'

# Metadata / QA.
road['TPG_ASSET'] = 'Ground109 Road 30ft Single Lane v1.2'
road['LENGTH_M'] = LENGTH
road['TRAVELED_WIDTH_M'] = TRAVEL_W
road['OVERALL_WIDTH_M'] = OVERALL_W
road['ASPECT_RATIO_LENGTH_TO_WIDTH'] = LENGTH / OVERALL_W
road['RAMP_LENGTH_M'] = RAMP_LEN
road['CROWN_HEIGHT_M'] = CROWN_Z
road['COLLISION_BOTTOM_Z_M'] = COLL_BOTTOM_Z
road['NO_TEXTURED_VERTICAL_FACES'] = True
road['REFERENCE_PATTERN'] = 'separate render surface + collision shell as in attached asphaltStreet EDM'

assert abs(LENGTH / FT - 30.0) < 1e-9
assert abs(TRAVEL_W / FT - 8.0) < 1e-9
assert abs(OVERALL_W / FT - 9.0) < 1e-9
assert abs((LENGTH / OVERALL_W) - (30.0 / 9.0)) < 1e-9
# Center of both head-on ends is terrain height.
assert abs(verts[2][2] - TERRAIN_Z) < 1e-9
assert abs(verts[(ny - 1) * nx + 2][2] - TERRAIN_Z) < 1e-9

print('[TPG ROAD v1.2] SINGLE LANE - exact visible footprint 30.000 ft LONG x 9.000 ft overall')
print('[TPG ROAD v1.2] 8.000 ft traveled strip + 0.500 ft terrain feather each side')
print(f'[TPG ROAD v1.2] length:width aspect ratio = {LENGTH / OVERALL_W:.3f}:1')
print('[TPG ROAD v1.2] both head-on ends use 4 ft two-stage drive-on ramps to terrain height')
print('[TPG ROAD v1.2] visual mesh = top surface only; ZERO textured vertical faces/end caps')
print('[TPG ROAD v1.2] exact Ground109 Color + NormalGL + AO/Roughness-derived RoughMet')
print(f'[TPG ROAD v1.2] separate collision shell follows top and is buried to z={COLL_BOTTOM_Z:.3f}m')
