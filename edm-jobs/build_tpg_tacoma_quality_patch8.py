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

# The photo-derived hero body is generated with from_pydata(), unlike Blender
# primitives, so it does not inherit a UV layer.  ED's default material exporter
# requires a valid UV channel as soon as the Quicksand PBR/AORMS material is
# encountered.  Add a deterministic UVMap to every mesh that lacks one and fill
# it with a stable XY projection.  This preserves geometry while making the
# material/UV contract explicit for intact, LOD and destroyed exports.
uv_fixed = 0
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons:
        continue
    me = obj.data
    if len(me.uv_layers) == 0:
        uv = me.uv_layers.new(name='UVMap')
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        dx = max(xmax - xmin, 1e-6)
        dy = max(ymax - ymin, 1e-6)
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                co = me.vertices[vi].co
                uv.data[li].uv = ((co.x - xmin) / dx, (co.y - ymin) / dy)
        me.uv_layers.active = uv
        try:
            uv.active_render = True
        except Exception:
            pass
        uv_fixed += 1

bpy.context.scene.frame_set(100)
print(f'[TPG TACOMA] quality patch8 complete: slab masking core removed; legacy topper rack removed; UVMap added to {uv_fixed} meshes')
