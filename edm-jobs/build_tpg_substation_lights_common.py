import bpy, math, os, runpy, sys
from pathlib import Path
from mathutils import Vector

WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
EDM_JOBS = WORKSPACE / "edm-jobs"
if str(EDM_JOBS) not in sys.path:
    sys.path.insert(0, str(EDM_JOBS))

import tpg_substation_common as common

# This wrapper leaves the proven high-fidelity substation generator untouched and
# decorates only its existing LIGHTHEAD_* fixtures. build_tpg_substation.py uses
# `from tpg_substation_common import *`, so replacing common.box before runpy means
# the exact same geometry/layout is built while each existing yard light receives
# a lens plus an official Blender SPOT light exported by ED's EDM exporter.
_base_box = common.box
_destroyed = os.environ.get("TPG_SUB_DESTROYED", "0") == "1"


def _add_real_yard_light(name, loc, rot):
    x, y, z = loc
    M = common.mats()

    # Thin luminous-looking lens physically seated on the underside of the existing
    # fixture. Actual illumination comes from the EDM spot-light node below.
    _base_box(
        name + "_LENS",
        (x, y + 0.37, z - 0.155),
        (0.72, 0.38, 0.028),
        M["white"],
        0.008,
        rot=rot,
    )

    # Destroyed shape intentionally has no live light source.
    if _destroyed:
        return

    data = bpy.data.lights.new(name=name + "_EDM_SPOT_DATA", type="SPOT")
    data.energy = 550.0
    data.color = (1.0, 0.84, 0.62)
    data.use_custom_distance = True
    data.cutoff_distance = 32.0
    data.spot_size = math.radians(66.0)
    data.spot_blend = 0.48
    data.shadow_soft_size = 0.42
    data.specular_factor = 0.55

    light = bpy.data.objects.new(name + "_EDM_SPOT", data)
    bpy.context.collection.objects.link(light)
    light.location = (x, y + 0.34, z - 0.19)

    # Aim the fixture down and modestly toward the yard center rather than making
    # nine perfectly vertical circular pools of light.
    target = Vector((x * 0.78, y * 0.78, 0.25))
    direction = target - Vector(light.location)
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    props = common.get_edm_props(light)
    if hasattr(props, "LIGHT_SOFTNESS"):
        props.LIGHT_SOFTNESS = 0.55
    if hasattr(props, "LIGHT_VOLUME_RADIUS_FACTOR"):
        props.LIGHT_VOLUME_RADIUS_FACTOR = 1.0
    if hasattr(props, "LIGHT_VOLUME_DENSITY_FACTOR"):
        props.LIGHT_VOLUME_DENSITY_FACTOR = 0.12
    if hasattr(props, "LIGHT_VOLUME_NEAR_DISTANCE"):
        props.LIGHT_VOLUME_NEAR_DISTANCE = 0.25


def lights_box(name, loc, scale, mat, bevel=.04, rot=(0, 0, 0), coll=False):
    obj = _base_box(name, loc, scale, mat, bevel, rot=rot, coll=coll)
    if name.startswith("LIGHTHEAD_"):
        _add_real_yard_light(name, loc, rot)
    return obj


common.box = lights_box
runpy.run_path("edm-jobs/build_tpg_substation.py", run_name="__main__")
print("TPG Electrical Substation LIGHTS build decoration complete")
