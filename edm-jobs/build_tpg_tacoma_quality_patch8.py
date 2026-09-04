import runpy
import bpy

# Export-safe visual correction layered on the validated v6 build.  The v6 clay
# QA proved the full-height HERO_BODY_CORE extrusion was masking the actual
# Tacoma cab/hood/bed geometry and producing the false slab/van silhouette.
# Remove only that masking volume here; all photo-derived v6 panels, glazing,
# hood, grille, lamps, camper shell, accessories, wheel rig, LOD and damage
# pipeline stay untouched.
runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch6.py', run_name='__main__')

o = bpy.data.objects.get('HERO_BODY_CORE')
if o:
    bpy.data.objects.remove(o, do_unlink=True)

# Enforce the requested single low-profile rack by removing the legacy topper
# rack only.  Keep the forward/cab rack and its proven exporter-safe geometry.
for obj in list(bpy.data.objects):
    n = obj.name
    if n.startswith('RACK_RAIL_-1.84') or n.startswith('RACK_BAR_-1.84'):
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch8 complete: slab masking core removed; legacy topper rack removed')
