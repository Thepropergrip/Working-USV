import bpy, os, sys
from pathlib import Path
from mathutils import Vector

# BUILD 8 DIAGNOSTIC: geometry + EDM connectors ONLY.
# DCS 2.9.29.27468 rejects the Blender-exported EDM SpotLight node with
# "Wrong light version", even when exported with the current official ED exporter.
# Therefore this scene deliberately contains ZERO Blender LIGHT objects.
# The DCS-side Lua owns the actual spotlights and references the named connectors.

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

# Conventional renderable geometry at the origin.
common.box(
    'TPG_LIGHT_RIG_BURIED_ANCHOR',
    (0.0, 0.0, -0.45),
    (0.70, 0.70, 0.25),
    anchor_mat,
    bevel=0.0,
)

# Explicit bounds covering the whole rig. These are control objects, not render meshes.
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


def make_connector(name, location, rotation):
    empty = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(empty)
    empty.empty_display_type = 'ARROWS'
    empty.empty_display_size = 0.50
    empty.location = location
    empty.rotation_euler = rotation
    props = get_edm_props(empty)
    props.SPECIAL_TYPE = 'CONNECTOR'
    if hasattr(props, 'CONNECTOR_EXT'):
        props.CONNECTOR_EXT = ''
    return empty


for i, (x, y, z) in enumerate(LIGHTS):
    mast_bottom = YARD_RISE
    mast_top = z - 0.35
    mast_h = mast_top - mast_bottom

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
    common.box(
        f'TPG_RIG_DIAG_CROSSBAR_{i:02d}',
        (x, y, z - 0.42),
        (1.50, 0.18, 0.18),
        mast_mat,
        bevel=0.03,
    )

    light_pos = Vector((x, y, z - 0.18))
    target = Vector((x * 0.72, y * 0.72, 0.30))
    direction = target - light_pos
    aim_rot = direction.to_track_quat('-Z', 'Y').to_euler()
    make_connector(f'TPG_YARD_SPOT_{i}', light_pos, aim_rot)

# Hard assertion: the rejected pyedm SpotLight path must not exist in this scene.
light_objects = [o.name for o in bpy.context.scene.objects if o.type == 'LIGHT']
if light_objects:
    raise RuntimeError(f'BUILD 8 must contain no Blender LIGHT objects, found: {light_objects}')

print(
    f'TPG Substation Light Rig BUILD 8 built: {len(LIGHTS)} visible magenta masts, '
    f'{len(LIGHTS)} EDM connectors, BOUNDING_BOX {size}, LIGHT_BOX, ZERO embedded light nodes'
)
