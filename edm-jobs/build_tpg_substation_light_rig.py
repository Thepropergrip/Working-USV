import bpy, math, os, sys
from pathlib import Path
from mathutils import Vector

# DIAGNOSTIC dedicated light rig for the TPG electrical substation.
# This build intentionally uses exaggerated visible geometry so we can prove whether
# DCS instantiates the asset at all. Nine full-height high-visibility masts sit at the
# exact light positions, with oversized emissive lamp heads and the same real EDM spot
# lights used by the prior rig.

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import tpg_substation_common as common
from objects_custom_props import get_edm_props
from enums import NodeSocketInDefaultEnum

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

# Proper ED materials. Magenta masts are intentionally unnatural and highly visible
# in daylight; emissive heads remain obvious at night even if the real light nodes fail.
mast_mat = common.edm_mat(
    'TPG_LIGHT_RIG_DIAG_Magenta',
    (0.95, 0.02, 0.68),
    rough=0.42,
    metal=0.08,
    variation=0.008,
)
base_mat = common.edm_mat(
    'TPG_LIGHT_RIG_DIAG_Base',
    (0.95, 0.18, 0.02),
    rough=0.55,
    metal=0.05,
    variation=0.008,
)
head_mat = common.edm_mat(
    'TPG_LIGHT_RIG_DIAG_Head',
    (1.0, 0.82, 0.42),
    rough=0.20,
    metal=0.02,
    variation=0.004,
)
# Reuse the head base-color texture as an emissive source.
try:
    group = head_mat.node_tree.nodes.get('Group')
    tex = next(n for n in head_mat.node_tree.nodes if n.bl_idname == 'ShaderNodeTexImage')
    head_mat.node_tree.links.new(tex.outputs['Color'], group.inputs[NodeSocketInDefaultEnum.EMISSIVE])
    group.inputs[NodeSocketInDefaultEnum.EMISSIVE_VALUE].default_value = 12.0
except Exception as exc:
    print(f'TPG DIAG emissive setup warning: {exc}')

anchor_mat = common.edm_mat(
    'TPG_LIGHT_RIG_Anchor',
    (0.015, 0.015, 0.015),
    rough=0.92,
    metal=0.0,
    variation=0.005,
)

# Ordinary renderable geometry at origin.
common.box(
    'TPG_LIGHT_RIG_BURIED_ANCHOR',
    (0.0, 0.0, -0.45),
    (0.70, 0.70, 0.25),
    anchor_mat,
    bevel=0.0,
)

# Explicit EDM bounds covering the entire diagnostic rig.
min_x = min(p[0] for p in LIGHTS) - 1.5
max_x = max(p[0] for p in LIGHTS) + 1.5
min_y = min(p[1] for p in LIGHTS) - 1.5
max_y = max(p[1] for p in LIGHTS) + 1.5
min_z = -0.75
max_z = max(p[2] for p in LIGHTS) + 1.25
center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0)
size = (max_x - min_x, max_y - min_y, max_z - min_z)

bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
bbox = bpy.context.object
bbox.name = 'TPG_LIGHT_RIG_EXPLICIT_BOUNDING_BOX'
bbox.dimensions = size
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
get_edm_props(bbox).SPECIAL_TYPE = 'BOUNDING_BOX'

bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
lightbox = bpy.context.object
lightbox.name = 'TPG_LIGHT_RIG_EXPLICIT_LIGHT_BOX'
lightbox.dimensions = (size[0] + 10.0, size[1] + 10.0, size[2] + 6.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
get_edm_props(lightbox).SPECIAL_TYPE = 'LIGHT_BOX'

for i, (x, y, z) in enumerate(LIGHTS):
    mast_bottom = YARD_RISE
    mast_top = z - 0.35
    mast_h = mast_top - mast_bottom

    # Big orange base plate, fluorescent-magenta 8 m mast, and oversized emissive head.
    common.box(
        f'TPG_RIG_DIAG_BASE_{i:02d}',
        (x, y, YARD_RISE + 0.08),
        (1.10, 1.10, 0.16),
        base_mat,
        bevel=0.04,
    )
    common.cyl(
        f'TPG_RIG_DIAG_MAST_{i:02d}',
        (x, y, mast_bottom + mast_h / 2.0),
        0.22,
        mast_h,
        mast_mat,
        verts=36,
    )
    common.box(
        f'TPG_RIG_DIAG_HEAD_{i:02d}',
        (x, y, z),
        (1.10, 0.72, 0.42),
        head_mat,
        bevel=0.06,
    )
    # Small crossbar to make the mast silhouette unmistakable.
    common.box(
        f'TPG_RIG_DIAG_CROSSBAR_{i:02d}',
        (x, y, z - 0.42),
        (1.50, 0.18, 0.18),
        mast_mat,
        bevel=0.03,
    )

    data = bpy.data.lights.new(name=f'TPG_RIG_SPOT_{i:02d}_DATA', type='SPOT')
    data.energy = 6500.0
    data.color = (1.0, 0.84, 0.62)
    data.use_custom_distance = True
    data.cutoff_distance = 90.0
    data.spot_size = math.radians(80.0)
    data.spot_blend = 0.62
    data.shadow_soft_size = 0.55
    data.specular_factor = 0.70

    obj = bpy.data.objects.new(f'TPG_RIG_SPOT_{i:02d}', data)
    bpy.context.collection.objects.link(obj)
    obj.location = (x, y, z - 0.18)

    target = Vector((x * 0.72, y * 0.72, 0.30))
    direction = target - Vector(obj.location)
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    props = get_edm_props(obj)
    for attr, val in (
        ('LIGHT_SOFTNESS', 0.60),
        ('LIGHT_VOLUME_RADIUS_FACTOR', 1.0),
        ('LIGHT_VOLUME_DENSITY_FACTOR', 0.12),
        ('LIGHT_VOLUME_NEAR_DISTANCE', 0.20),
    ):
        if hasattr(props, attr):
            setattr(props, attr, val)

print(
    f'TPG Substation Light Rig DIAGNOSTIC built: {len(LIGHTS)} visible 8m magenta masts, '
    f'oversized emissive heads, EDM spot lights, BOUNDING_BOX {size}, and LIGHT_BOX'
)
