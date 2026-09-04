import bpy, math, os, sys
from pathlib import Path
from mathutils import Vector

# Dedicated light rig for the TPG electrical substation.
# The visible substation remains a separate asset. This rig supplies nine real EDM
# spot lights plus real ED-material lamp-head geometry, an explicit EDM BOUNDING_BOX,
# and an explicit EDM LIGHT_BOX. Earlier builds used plain Blender materials; the ED
# exporter reported those meshes as 0 triangles, leaving a light-only EDM that DCS
# rejected with "Model has invalid bounding box".

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import tpg_substation_common as common
from objects_custom_props import get_edm_props

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

YARD_RISE = 0.4572
LIGHTS = [
    (-50.0, -31.0, 8.0 + YARD_RISE),
    (-32.0, -31.0, 8.0 + YARD_RISE),
    (-10.0, -31.0, 8.0 + YARD_RISE),
    ( 12.0, -31.0, 8.0 + YARD_RISE),
    ( 34.0, -31.0, 8.0 + YARD_RISE),
    ( 51.0, -18.0, 8.0 + YARD_RISE),
    ( 51.0,   6.0, 8.0 + YARD_RISE),
    ( 51.0,  28.0, 8.0 + YARD_RISE),
    (-50.0,  30.0, 8.0 + YARD_RISE),
]

# Real ED default materials. These produce actual exported triangles and texture
# references instead of the zero-triangle result from ordinary Blender materials.
lamp_mat = common.edm_mat(
    'TPG_LIGHT_RIG_LampHead',
    (0.72, 0.56, 0.30),
    rough=0.48,
    metal=0.10,
    variation=0.01,
)
anchor_mat = common.edm_mat(
    'TPG_LIGHT_RIG_Anchor',
    (0.015, 0.015, 0.015),
    rough=0.92,
    metal=0.0,
    variation=0.005,
)

# Small buried real mesh near origin. This is not the bounding box itself; it simply
# guarantees ordinary renderable geometry exists in the EDM.
common.box(
    'TPG_LIGHT_RIG_BURIED_ANCHOR',
    (0.0, 0.0, -0.45),
    (0.70, 0.70, 0.25),
    anchor_mat,
    bevel=0.0,
)

# Explicit EDM bounding box spanning every emitter and the ground-side anchor.
# Official ED exporter maps SPECIAL_TYPE='BOUNDING_BOX' to model.setBBox().
min_x = min(p[0] for p in LIGHTS) - 1.0
max_x = max(p[0] for p in LIGHTS) + 1.0
min_y = min(p[1] for p in LIGHTS) - 1.0
max_y = max(p[1] for p in LIGHTS) + 1.0
min_z = -0.75
max_z = max(p[2] for p in LIGHTS) + 0.75
center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0)
size = (max_x - min_x, max_y - min_y, max_z - min_z)

bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
bbox = bpy.context.object
bbox.name = 'TPG_LIGHT_RIG_EXPLICIT_BOUNDING_BOX'
bbox.dimensions = size
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
get_edm_props(bbox).SPECIAL_TYPE = 'BOUNDING_BOX'

# Separate light box slightly larger than the physical bounds so DCS has a defined
# light-culling volume around all nine emitters.
bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
lightbox = bpy.context.object
lightbox.name = 'TPG_LIGHT_RIG_EXPLICIT_LIGHT_BOX'
lightbox.dimensions = (size[0] + 8.0, size[1] + 8.0, size[2] + 4.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
get_edm_props(lightbox).SPECIAL_TYPE = 'LIGHT_BOX'

for i, (x, y, z) in enumerate(LIGHTS):
    # Actual exported lamp head at every emitter. These are small enough to sit
    # inside the visible substation fixture when both assets share coordinates.
    common.box(
        f'TPG_RIG_HEAD_{i:02d}',
        (x, y, z),
        (0.44, 0.28, 0.14),
        lamp_mat,
        bevel=0.02,
    )

    data = bpy.data.lights.new(name=f'TPG_RIG_SPOT_{i:02d}_DATA', type='SPOT')
    data.energy = 5200.0
    data.color = (1.0, 0.84, 0.62)
    data.use_custom_distance = True
    data.cutoff_distance = 78.0
    data.spot_size = math.radians(76.0)
    data.spot_blend = 0.62
    data.shadow_soft_size = 0.55
    data.specular_factor = 0.70

    obj = bpy.data.objects.new(f'TPG_RIG_SPOT_{i:02d}', data)
    bpy.context.collection.objects.link(obj)
    obj.location = (x, y, z - 0.04)

    target = Vector((x * 0.72, y * 0.72, 0.30))
    direction = target - Vector(obj.location)
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    props = get_edm_props(obj)
    for attr, val in (
        ('LIGHT_SOFTNESS', 0.60),
        ('LIGHT_VOLUME_RADIUS_FACTOR', 1.0),
        ('LIGHT_VOLUME_DENSITY_FACTOR', 0.10),
        ('LIGHT_VOLUME_NEAR_DISTANCE', 0.20),
    ):
        if hasattr(props, attr):
            setattr(props, attr, val)

print(
    f'TPG Substation Light Rig built with {len(LIGHTS)} EDM spot lights, '
    f'real ED-material emitter meshes, explicit BOUNDING_BOX {size}, and LIGHT_BOX'
)
