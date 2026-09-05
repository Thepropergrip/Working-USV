import bpy, math, os, runpy, sys
from pathlib import Path
from mathutils import Vector

WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
EDM_JOBS = WORKSPACE / "edm-jobs"
if str(EDM_JOBS) not in sys.path:
    sys.path.insert(0, str(EDM_JOBS))

import tpg_substation_common as common

# LIGHTS v1.0.1: keep the proven substation geometry/layout untouched and decorate
# only the existing LIGHTHEAD_* fixtures.  The first LIGHTS build used Blender
# SPOT objects alone; DCS can display those in ModelViewer yet ignore them on
# static/ground objects in-game.  This revision therefore exports three layers:
#   1) a self-illuminated EDM lens,
#   2) a named EDM CONNECTOR for the DCS Lua light system,
#   3) the embedded EDM SPOT as a secondary fallback.
_base_box = common.box
_destroyed = os.environ.get("TPG_SUB_DESTROYED", "0") == "1"
_emissive_lens_mat = None


def _lens_material():
    global _emissive_lens_mat
    if _emissive_lens_mat is not None:
        return _emissive_lens_mat

    m = common.edm_mat(
        "TPG_SUB100_LIGHTS_WarmLens",
        (1.0, 0.78, 0.48),
        rough=0.18,
        metal=0.0,
        variation=0.006,
        streak=False,
        soot=False,
    )
    group = next((n for n in m.node_tree.nodes if n.name == "Group"), None)
    tex = next((n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeTexImage"), None)
    if group is not None and tex is not None:
        try:
            m.node_tree.links.new(tex.outputs["Color"], group.inputs[common.NodeSocketInDefaultEnum.EMISSIVE])
            group.inputs[common.NodeSocketInDefaultEnum.EMISSIVE_VALUE].default_value = 6.0
        except Exception as exc:
            print("TPG LIGHTS emissive setup warning:", exc)
    _emissive_lens_mat = m
    return m


def _make_connector(name, location, rotation):
    empty = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(empty)
    empty.empty_display_type = "ARROWS"
    empty.empty_display_size = 0.35
    empty.location = location
    empty.rotation_euler = rotation
    props = common.get_edm_props(empty)
    props.SPECIAL_TYPE = "CONNECTOR"
    if hasattr(props, "CONNECTOR_EXT"):
        props.CONNECTOR_EXT = ""
    return empty


def _add_real_yard_light(name, loc, rot):
    x, y, z = loc

    # Physical glowing lens seated under the existing fixture.  It remains visible
    # even on DCS builds where static-object projected lights are restricted.
    _base_box(
        name + "_LENS",
        (x, y + 0.37, z - 0.155),
        (0.72, 0.38, 0.028),
        _lens_material(),
        0.008,
        rot=rot,
    )

    # Destroyed shape has dead fixtures: emissive lens is replaced by a dark insert
    # and no connector/spot node is exported.
    if _destroyed:
        return

    light_pos = Vector((x, y + 0.34, z - 0.19))
    target = Vector((x * 0.72, y * 0.72, 0.30))
    direction = target - light_pos
    aim_rot = direction.to_track_quat("-Z", "Y").to_euler()

    # DCS-managed light anchor. The package Lua references these exact names.
    idx = name.split("_")[-1]
    _make_connector(f"TPG_YARD_SPOT_{idx}", light_pos, aim_rot)

    # Secondary embedded EDM spotlight.  This is intentionally retained as a
    # fallback, but the primary in-game path is now connector + Lua GT.lights.
    data = bpy.data.lights.new(name=name + "_EDM_SPOT_DATA", type="SPOT")
    data.energy = 850.0
    data.color = (1.0, 0.82, 0.58)
    data.use_custom_distance = True
    data.cutoff_distance = 38.0
    data.spot_size = math.radians(72.0)
    data.spot_blend = 0.55
    data.shadow_soft_size = 0.55
    data.specular_factor = 0.65

    light = bpy.data.objects.new(name + "_EDM_SPOT", data)
    bpy.context.collection.objects.link(light)
    light.location = light_pos
    light.rotation_euler = aim_rot

    props = common.get_edm_props(light)
    if hasattr(props, "LIGHT_SOFTNESS"):
        props.LIGHT_SOFTNESS = 0.70
    if hasattr(props, "LIGHT_VOLUME_RADIUS_FACTOR"):
        props.LIGHT_VOLUME_RADIUS_FACTOR = 1.15
    if hasattr(props, "LIGHT_VOLUME_DENSITY_FACTOR"):
        props.LIGHT_VOLUME_DENSITY_FACTOR = 0.10
    if hasattr(props, "LIGHT_VOLUME_NEAR_DISTANCE"):
        props.LIGHT_VOLUME_NEAR_DISTANCE = 0.30


def lights_box(name, loc, scale, mat, bevel=.04, rot=(0, 0, 0), coll=False):
    obj = _base_box(name, loc, scale, mat, bevel, rot=rot, coll=coll)
    if name.startswith("LIGHTHEAD_"):
        _add_real_yard_light(name, loc, rot)
    return obj


common.box = lights_box
runpy.run_path("edm-jobs/build_tpg_substation.py", run_name="__main__")
print("TPG Electrical Substation LIGHTS connector/emissive build complete")
