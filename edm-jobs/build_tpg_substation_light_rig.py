import bpy, math, os, sys
from pathlib import Path
from mathutils import Vector

# Dedicated Massun-style light-only asset for the TPG electrical substation.
# This intentionally does NOT include the visible substation geometry. DCS is much
# more reliable at servicing dynamic lights when the light effect is its own object.

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights):
    pass

# Yard fixture coordinates from the proven substation builder.
# Z is the actual lamp emitter height after the raised yard offset.
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

# Add a tiny buried mesh so the EDM has a conventional scene root/extent while
# remaining visually invisible in normal use.
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, -1.25))
anchor = bpy.context.object
anchor.name = 'TPG_LIGHT_RIG_BURIED_ANCHOR'
anchor.scale = (0.10, 0.10, 0.10)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
mat = bpy.data.materials.new('TPG_LIGHT_RIG_DARK')
mat.diffuse_color = (0.005, 0.005, 0.005, 1.0)
anchor.data.materials.append(mat)

for i, (x, y, z) in enumerate(LIGHTS):
    data = bpy.data.lights.new(name=f'TPG_RIG_SPOT_{i:02d}_DATA', type='SPOT')
    # Deliberately much stronger than the failed embedded 550 W lights. The
    # exporter converts Blender power through ED's PBR light coefficients.
    data.energy = 4200.0
    data.color = (1.0, 0.84, 0.62)
    data.use_custom_distance = True
    data.cutoff_distance = 72.0
    data.spot_size = math.radians(72.0)
    data.spot_blend = 0.62
    data.shadow_soft_size = 0.55
    data.specular_factor = 0.70

    obj = bpy.data.objects.new(f'TPG_RIG_SPOT_{i:02d}', data)
    bpy.context.collection.objects.link(obj)
    obj.location = (x, y, z)

    # Aim broadly toward the center of the substation yard with a ground target
    # slightly above terrain to avoid a perfectly vertical pool.
    target = Vector((x * 0.72, y * 0.72, 0.30))
    direction = target - Vector(obj.location)
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # ED exporter custom light fields.
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

print(f'TPG Substation Light Rig built with {len(LIGHTS)} dedicated EDM spot lights')
