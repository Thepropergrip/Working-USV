import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch23.
# Priority: third-gen Tacoma grille/fascia depth and front bumper silhouette in front/front-3Q clay QA.
# Preserve all proven DCS behavior, animation arguments, LOD/destroyed structure,
# official ED exporter pipeline, and one-folder Mods/tech packaging.
ns23 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch23.py', run_name='__main__')
LOD = ns23['LOD']
mesh_obj = ns23['mesh_obj']
curve_tube = ns23['curve_tube']
remove = ns23['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

for name in ('HERO_P24_GRILLE_BACK','HERO_P24_GRILLE_FRAME','HERO_P24_LOWER_CHIN','HERO_P24_HOOD_NOSE_BREAK'):
    remove(name)
for side in (-1, 1):
    for stem in ('HERO_P24_BUMPER_WING_', 'HERO_P24_FASCIA_RETURN_'):
        remove(f'{stem}{side}')

panel('HERO_P24_GRILLE_BACK', [
    (2.585,-.445,1.155), (2.605,-.525,1.075), (2.625,-.470,.800),
    (2.635, .470,.800), (2.605, .525,1.075), (2.585, .445,1.155)
], black)

if LOD < 2:
    curve_tube('HERO_P24_GRILLE_FRAME', [
        (2.578,-.445,1.160), (2.602,-.535,1.075), (2.622,-.478,.795),
        (2.628, .478,.795), (2.602, .535,1.075), (2.578, .445,1.160),
        (2.578,-.445,1.160)
    ], .010, paint, 2)
    curve_tube('HERO_P24_HOOD_NOSE_BREAK', [
        (2.30,-.49,1.205), (2.48,-.43,1.185), (2.565,-.34,1.165),
        (2.565, .34,1.165), (2.48, .43,1.185), (2.30, .49,1.205)
    ], .006, black, 1)

for side in (-1, 1):
    s = side
    panel(f'HERO_P24_BUMPER_WING_{side}', [
        (2.60,s*.455,.790), (2.64,s*.525,.835), (2.60,s*.670,.865),
        (2.51,s*.760,.895), (2.40,s*.775,.835), (2.43,s*.690,.755),
        (2.54,s*.550,.735)
    ], paint)
    panel(f'HERO_P24_FASCIA_RETURN_{side}', [
        (2.54,s*.535,1.120), (2.58,s*.600,1.085), (2.56,s*.700,1.015),
        (2.49,s*.748,.930), (2.42,s*.735,.985), (2.48,s*.650,1.080)
    ], paint)

panel('HERO_P24_LOWER_CHIN', [
    (2.625,-.465,.795), (2.655,-.430,.735), (2.660,-.355,.690),
    (2.660, .355,.690), (2.655, .430,.735), (2.625, .465,.795)
], paint)

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
print('[TPG TACOMA] quality patch24 complete: recessed hex grille, hood nose break, clamp-like bumper wings and lower chin; DCS mechanics untouched')
