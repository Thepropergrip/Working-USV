import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch20.
# Priority: front-cab/A-pillar/roof-header silhouette in front and front-3Q clay QA.
# Preserve all proven DCS behavior, animation arguments, LOD/destroyed structure,
# official ED exporter pipeline, and one-folder Mods/tech packaging.
ns20 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch20.py', run_name='__main__')
LOD = ns20['LOD']
mesh_obj = ns20['ns19']['ns18']['ns17']['ns16']['ns15']['ns14']['ns13']['mesh_obj']
curve_tube = ns20['ns19']['ns18']['ns17']['ns16']['ns15']['ns14']['ns13']['curve_tube']
remove = ns20['ns19']['ns18']['ns17']['ns16']['ns15']['ns14']['ns13']['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

# Idempotent cleanup for reruns.
for n in ('HERO_P21_ROOF_HEADER','HERO_P21_HEADER_BREAK'):
    remove(n)
for side in (-1,1):
    for stem in ('HERO_P21_A_PILLAR_SKIN_','HERO_P21_A_PILLAR_EDGE_','HERO_P21_ROOF_CORNER_'):
        remove(f'{stem}{side}')

# The previous windshield face established the rake, but the surrounding painted
# cab still read too rectangular. Add tapered painted A-pillar skins outside the
# glass so the cab narrows toward the roof and gains the heavier Tacoma corner.
for side in (-1,1):
    s = side
    panel(f'HERO_P21_A_PILLAR_SKIN_{side}',[
        (.900,s*.715,1.195),(.905,s*.665,1.205),
        (.590,s*.605,1.665),(.555,s*.655,1.680),
        (.660,s*.690,1.535),(.790,s*.710,1.355)
    ],paint)
    if LOD < 2:
        curve_tube(f'HERO_P21_A_PILLAR_EDGE_{side}',[
            (.905,s*.714,1.205),(.790,s*.710,1.355),(.660,s*.690,1.535),(.555,s*.655,1.680)
        ],.0055,black,1)

# Roof leading edge: gently crowned and narrower than the cowl. This removes the
# slab-roof read visible in 3Q while keeping the long double-cab roof proportions.
panel('HERO_P21_ROOF_HEADER',[
    (.555,-.655,1.680),(.520,-.500,1.715),(.505,0.0,1.735),
    (.520,.500,1.715),(.555,.655,1.680),(.445,.625,1.705),
    (.420,0.0,1.755),(.445,-.625,1.705)
],paint)

if LOD < 2:
    curve_tube('HERO_P21_HEADER_BREAK',[
        (.555,-.655,1.685),(.520,-.500,1.718),(.505,0.0,1.738),
        (.520,.500,1.718),(.555,.655,1.685)
    ],.0045,black,1)
    for side in (-1,1):
        s = side
        curve_tube(f'HERO_P21_ROOF_CORNER_{side}',[
            (.555,s*.655,1.685),(.445,s*.625,1.710),(.330,s*.610,1.725)
        ],.0045,black,1)

# Exporter UV safety for newly generated meshes.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons or len(obj.data.uv_layers):
        continue
    me = obj.data
    uv = me.uv_layers.new(name='UVMap')
    xs=[v.co.x for v in me.vertices]; ys=[v.co.y for v in me.vertices]
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
    dx=max(xmax-xmin,1e-6); dy=max(ymax-ymin,1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=((co.x-xmin)/dx,(co.y-ymin)/dy)
    me.uv_layers.active=uv

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch21 complete: tapered painted A-pillars and crowned/narrowed roof header for a more Tacoma-specific front-cab silhouette; DCS mechanics untouched')
