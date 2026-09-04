import bpy, math, os, sys
from pathlib import Path
from mathutils import Vector

# Dedicated light rig for the TPG electrical substation.
# The visible substation remains a separate asset. This rig supplies nine real EDM
# spot lights plus tiny physical lamp-head meshes so DCS has a valid model bounding
# volume spanning every emitter. A previous near-empty/light-only EDM was rejected
# in-game with "Model has invalid bounding box".

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

# Conventional material for the tiny lamp-head meshes. These are intentionally
# very small; when overlaid on the real substation they sit inside/under the
# existing fixture heads and should not materially change the visible asset.
lamp_mat = bpy.data.materials.new('TPG_LIGHT_RIG_LAMP_HEAD')
lamp_mat.diffuse_color = (1.0, 0.82, 0.55, 1.0)

# A buried center anchor guarantees the model also owns a conventional ground-side
# mesh near its origin.
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, -0.35))
anchor = bpy.context.object
anchor.name = 'TPG_LIGHT_RIG_BURIED_ANCHOR'
anchor.scale = (0.35, 0.35, 0.15)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
anchor.data.materials.append(lamp_mat)

for i, (x, y, z) in enumerate(LIGHTS):
    # Physical lamp head establishes a valid EDM bounding volume at every light
    # location/height. Dimensions remain small enough to hide inside the real
    # substation fixture when both objects share coordinates and heading.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z))
    head = bpy.context.object
    head.name = f'TPG_RIG_HEAD_{i:02d}'
    head.scale = (0.22, 0.14, 0.07)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    head.data.materials.append(lamp_mat)

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

    props = getattr(obj, 'EDMProps', None)
    if props is None:
        try:
            from objects_custom_props import get_edm_props
            props = get_edm_props(obj)
        except Exception:
            props = None
    if props is not None:
        for attr, val in (
            ('LIGHT_SOFTNESS', 0.60),
            ('LIGHT_VOLUME_RADIUS_FACTOR', 1.0),
            ('LIGHT_VOLUME_DENSITY_FACTOR', 0.10),
            ('LIGHT_VOLUME_NEAR_DISTANCE', 0.20),
        ):
            if hasattr(props, attr):
                setattr(props, attr, val)

print(f'TPG Substation Light Rig built with {len(LIGHTS)} EDM spot lights and physical emitter bounds')
