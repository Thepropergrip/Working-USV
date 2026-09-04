import runpy
import bpy

# Build through the current visual/material quality pass first.
runpy.run_path("edm-jobs/build_tpg_tacoma_quality_patch3.py", run_name="__main__")

# Keep world transform while attaching added wheel-face geometry to the existing
# DCS argument-8 roll joints. Define this locally instead of depending on a
# nested runpy namespace, which is not guaranteed to re-export helper symbols.
def parent_keep(child, parent):
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw

# The added TRD face detail must be part of each wheel's roll joint, not static chassis decoration.
parents = {
    ('F','-1'): 'FBX_Cylinder_ROLL',
    ('R','-1'): 'FBX_Cylinder.001_ROLL',
    ('F','1'):  'FBX_Cylinder.002_ROLL',
    ('R','1'):  'FBX_Cylinder.003_ROLL',
}
for (axle,side), pname in parents.items():
    pa = bpy.data.objects.get(pname)
    if pa is None:
        raise RuntimeError(f'Missing Tacoma wheel roll parent {pname}')
    prefixes = (
        f'TRD_RIM_LIP_{axle}_{side}',
        f'TRD_HUB_{axle}_{side}',
        f'TRD_SPOKE_{axle}_{side}_',
        f'TRD_LUG_{axle}_{side}_',
    )
    count = 0
    for o in list(bpy.data.objects):
        if any(o.name.startswith(x) for x in prefixes):
            parent_keep(o, pa)
            count += 1
    print(f'[TPG TACOMA] parented {count} TRD face objects to {pname}')

# Export must remain at neutral argument state.
bpy.context.scene.frame_set(100)
