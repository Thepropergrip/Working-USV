import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch24.
# Priority: 2016 third-gen Tacoma slim swept headlamp/fender interface and hood-brow silhouette
# in front/front-3Q clay QA. Preserve all proven DCS mechanics and packaging.
ns24 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch24.py', run_name='__main__')
LOD = ns24['LOD']
mesh_obj = ns24['mesh_obj']
curve_tube = ns24['curve_tube']
remove = ns24['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

for side in (-1, 1):
    for stem in ('HERO_P25_LAMP_RECESS_', 'HERO_P25_LAMP_BROW_', 'HERO_P25_FENDER_TIE_', 'HERO_P25_HOOD_EDGE_'):
        remove(f'{stem}{side}')

# Third-gen Tacoma lamps are visually slim and high, with the outer end swept into the fender.
# Keep the recess shallow so this remains silhouette/form work rather than accessory polish.
for side in (-1, 1):
    s = side
    panel(f'HERO_P25_LAMP_RECESS_{side}', [
        (2.555,s*.455,1.135), (2.575,s*.535,1.115), (2.555,s*.655,1.095),
        (2.500,s*.745,1.075), (2.420,s*.780,1.055), (2.385,s*.745,1.095),
        (2.445,s*.620,1.125), (2.505,s*.505,1.145)
    ], black)

    # Painted upper brow gives the front clip the characteristic tight hood-to-lamp tension.
    panel(f'HERO_P25_LAMP_BROW_{side}', [
        (2.510,s*.470,1.175), (2.515,s*.575,1.165), (2.470,s*.690,1.145),
        (2.405,s*.785,1.120), (2.365,s*.800,1.145), (2.410,s*.690,1.185),
        (2.455,s*.565,1.195)
    ], paint)

    # Blend the lamp outer point into the already-developed fender crown instead of leaving a flat fascia slab.
    panel(f'HERO_P25_FENDER_TIE_{side}', [
        (2.405,s*.785,1.120), (2.350,s*.835,1.105), (2.270,s*.875,1.095),
        (2.180,s*.895,1.085), (2.150,s*.875,1.145), (2.245,s*.845,1.175),
        (2.335,s*.810,1.165)
    ], paint)

    if LOD < 2:
        curve_tube(f'HERO_P25_HOOD_EDGE_{side}', [
            (2.30,s*.500,1.215), (2.42,s*.485,1.205), (2.50,s*.455,1.190),
            (2.555,s*.405,1.175)
        ], .005, black, 1)

# Ensure generated mesh objects remain export-safe with simple UVs.
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
print('[TPG TACOMA] quality patch25 complete: slim swept lamp recesses, painted brows, fender ties and hood-edge tension; DCS mechanics untouched')
