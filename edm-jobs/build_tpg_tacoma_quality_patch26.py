import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch25.
# Priority: make the long-bed topper read as a fitted Tacoma shell rather than a generic box
# in side/rear-3Q clay QA. Preserve all proven DCS mechanics and packaging.
ns25 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch25.py', run_name='__main__')
LOD = ns25['LOD']
mesh_obj = ns25['mesh_obj']
curve_tube = ns25['curve_tube']
remove = ns25['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

for n in ('HERO_P26_CAP_FRONT_CROWN','HERO_P26_CAP_REAR_HEADER','HERO_P26_CAP_REAR_SKIRT'):
    remove(n)
for side in (-1, 1):
    for stem in ('HERO_P26_CAP_SHOULDER_', 'HERO_P26_CAP_SILL_', 'HERO_P26_CAP_REAR_EDGE_'):
        remove(f'{stem}{side}')

# Refine the shell front/header so the cap visually keys into the Tacoma cab roof but
# remains a distinct bed-mounted volume. The leading edge is slightly lower and narrower
# than the mid-cap crown, eliminating the remaining slab-like front face.
panel('HERO_P26_CAP_FRONT_CROWN', [
    (-1.055,-.610,1.676), (-1.105,-.655,1.704), (-1.180,-.560,1.724),
    (-1.205,0.0,1.748), (-1.180,.560,1.724), (-1.105,.655,1.704),
    (-1.055,.610,1.676), (-1.020,0.0,1.705)
], paint)

# Give each side a continuous shoulder from the cab-adjacent front of the topper to the
# pinched rear corner. This is silhouette work: broadest through the bed, then tapering
# inward before the hatch rather than ending as a rectangular camper box.
for side in (-1, 1):
    s = side
    panel(f'HERO_P26_CAP_SHOULDER_{side}', [
        (-1.10,s*.655,1.700), (-1.35,s*.770,1.706), (-2.35,s*.778,1.700),
        (-2.78,s*.748,1.674), (-2.98,s*.665,1.635), (-2.93,s*.700,1.590),
        (-2.70,s*.760,1.642), (-1.40,s*.785,1.674)
    ], paint)
    if LOD < 2:
        curve_tube(f'HERO_P26_CAP_SILL_{side}', [
            (-1.28,s*.790,1.275), (-2.20,s*.792,1.275), (-2.80,s*.780,1.275)
        ], .0055, black, 1)
        curve_tube(f'HERO_P26_CAP_REAR_EDGE_{side}', [
            (-2.98,s*.665,1.635), (-3.02,s*.650,1.500), (-3.03,s*.625,1.300)
        ], .0060, black, 1)

# Crown the rear hatch header and add a restrained lower skirt so rear-3Q shows a
# deliberate fitted-shell termination instead of a flat vertical cut.
panel('HERO_P26_CAP_REAR_HEADER', [
    (-3.040,-.545,1.646), (-3.055,-.430,1.675), (-3.060,0.0,1.692),
    (-3.055,.430,1.675), (-3.040,.545,1.646), (-3.012,0.0,1.630)
], paint)
panel('HERO_P26_CAP_REAR_SKIRT', [
    (-3.050,-.650,1.185), (-3.065,-.560,1.255), (-3.070,.560,1.255),
    (-3.050,.650,1.185), (-2.995,.620,1.150), (-2.995,-.620,1.150)
], paint)

# Exporter UV safety for all newly generated visible meshes.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons or len(obj.data.uv_layers):
        continue
    me = obj.data
    uv = me.uv_layers.new(name='UVMap')
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
    dx = max(xmax-xmin, 1e-6); dy = max(ymax-ymin, 1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co.x-xmin)/dx, (co.y-ymin)/dy)
    me.uv_layers.active = uv

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch26 complete: fitted topper front crown, tapered side shoulders and crowned rear hatch termination; DCS mechanics untouched')
