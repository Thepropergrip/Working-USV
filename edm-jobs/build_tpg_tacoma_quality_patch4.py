import runpy
import bpy

ns = runpy.run_path("edm-jobs/build_tpg_tacoma_quality_patch3.py", run_name="__main__")
parent_keep = ns['parent_keep']

# The added TRD face detail must be part of each wheel's roll joint, not static chassis decoration.
parents = {
    ('F','-1'): 'FBX_Cylinder_ROLL',
    ('R','-1'): 'FBX_Cylinder.001_ROLL',
    ('F','1'):  'FBX_Cylinder.002_ROLL',
    ('R','1'):  'FBX_Cylinder.003_ROLL',
}
for (axle,side), pname in parents.items():
    pa=bpy.data.objects.get(pname)
    if pa is None:
        raise RuntimeError(f'Missing Tacoma wheel roll parent {pname}')
    prefixes=(f'TRD_RIM_LIP_{axle}_{side}',f'TRD_HUB_{axle}_{side}',f'TRD_SPOKE_{axle}_{side}_',f'TRD_LUG_{axle}_{side}_')
    count=0
    for o in list(bpy.data.objects):
        if any(o.name.startswith(x) for x in prefixes):
            parent_keep(o,pa);count+=1
    print(f'[TPG TACOMA] parented {count} TRD face objects to {pname}')

bpy.context.scene.frame_set(100)
