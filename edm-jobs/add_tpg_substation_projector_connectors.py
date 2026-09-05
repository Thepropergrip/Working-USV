import bpy
import math
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tpg_substation_common as common
from objects_custom_props import get_edm_props
from enums import NodeSocketInDefaultEnum

YARD_RISE = 0.4572
HEAD_Z = 7.8 + YARD_RISE
LIGHTS = [
    (-50.0, -31.0),
    (-32.0, -31.0),
    (-10.0, -31.0),
    ( 12.0, -31.0),
    ( 34.0, -31.0),
    ( 51.0, -18.0),
    ( 51.0,   6.0),
    ( 51.0,  28.0),
    (-50.0,  30.0),
]

# Visible warm lens so the actual fixtures are visibly illuminated at night.
lens_mat = common.edm_mat(
    "TPG_SUB_LIGHT_LENS",
    (1.0, 0.72, 0.36),
    rough=0.20,
    metal=0.0,
    variation=0.003,
)
try:
    group = lens_mat.node_tree.nodes.get("Group")
    tex = next(n for n in lens_mat.node_tree.nodes if n.bl_idname == "ShaderNodeTexImage")
    lens_mat.node_tree.links.new(tex.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.EMISSIVE])
    group.inputs[NodeSocketInDefaultEnum.EMISSIVE_VALUE].default_value = 18.0
except Exception as exc:
    print(f"TPG projector lens emissive warning: {exc}")


def make_connector(name, location, rotation):
    empty = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(empty)
    empty.empty_display_type = "ARROWS"
    empty.empty_display_size = 0.35
    empty.location = location
    empty.rotation_euler = rotation
    props = get_edm_props(empty)
    props.SPECIAL_TYPE = "CONNECTOR"
    if hasattr(props, "CONNECTOR_EXT"):
        props.CONNECTOR_EXT = ""
    return empty

for i, (x, y) in enumerate(LIGHTS):
    # Thin lens plate just outside the existing LIGHTHEAD geometry.
    common.box(
        f"TPG_LIGHT_LENS_{i:02d}",
        (x, y + 0.735, HEAD_Z - 0.03),
        (0.76, 0.025, 0.16),
        lens_mat,
        bevel=0.012,
        rot=(math.radians(-12.0), 0.0, 0.0),
    )

    # Connector points inward/down into the yard. Current official exporter supports
    # connectors correctly even though its embedded Light nodes are rejected by DCS.
    pos = Vector((x, y + 0.62, HEAD_Z - 0.12))
    target = Vector((x * 0.68, y * 0.68, YARD_RISE + 0.35))
    direction = target - pos
    rot = direction.to_track_quat('-Z', 'Y').to_euler()
    make_connector(f"TPG_YARD_FLOOD_{i}", pos, rot)

# Do not accidentally reintroduce the incompatible official-exporter Light nodes.
lights = [o.name for o in bpy.context.scene.objects if o.type == "LIGHT"]
if lights:
    raise RuntimeError(f"TPG projector build must contain zero Blender LIGHT objects: {lights}")

print(f"TPG projector connectors added: {len(LIGHTS)} connectors + emissive lenses, zero embedded light nodes")
