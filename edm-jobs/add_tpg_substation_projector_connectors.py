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

# Visible lens geometry only. Do NOT make this material permanently emissive: the
# actual legacy LightNode brightness is now controlled by DCS headlight argument 31,
# so daytime fixtures remain visually off instead of glowing all day.
lens_mat = common.edm_mat(
    "TPG_SUB_LIGHT_LENS",
    (0.72, 0.58, 0.38),
    rough=0.28,
    metal=0.0,
    variation=0.003,
)


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
    common.box(
        f"TPG_LIGHT_LENS_{i:02d}",
        (x, y + 0.735, HEAD_Z - 0.03),
        (0.76, 0.025, 0.16),
        lens_mat,
        bevel=0.012,
        rot=(math.radians(-12.0), 0.0, 0.0),
    )

    pos = Vector((x, y + 0.62, HEAD_Z - 0.12))

    # User test proved the legacy donor LightNode projects along the opposite local
    # axis from the modern connector test. Track +Z (not -Z) toward an inward target.
    # Every fixture therefore points down and toward the facility instead of radiating
    # outward in the prior spiral-like pattern.
    target = Vector((x * 0.30, y * 0.30, YARD_RISE + 0.55))
    direction = target - pos
    rot = direction.to_track_quat('Z', 'Y').to_euler()
    make_connector(f"TPG_YARD_FLOOD_{i}", pos, rot)

lights = [o.name for o in bpy.context.scene.objects if o.type == "LIGHT"]
if lights:
    raise RuntimeError(f"TPG projector build must contain zero Blender LIGHT objects: {lights}")

print(f"TPG projector connectors added: {len(LIGHTS)} inward-facing connectors, non-emissive daytime lenses, zero embedded modern light nodes")
