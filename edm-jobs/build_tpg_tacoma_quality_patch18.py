import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch17.
# Priority: windshield/cowl/front-cab relationship in front and front-3Q clay QA.
# DCS registration, 113 mph tuning, args 8/9, LOD/destroyed structure,
# official ED exporter pipeline and Mods/tech packaging remain untouched.
ns17 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch17.py', run_name='__main__')
LOD = ns17['LOD']
mesh_obj = ns17['ns16']['ns15']['ns14']['ns13']['mesh_obj']
curve_tube = ns17['ns16']['ns15']['ns14']['ns13']['curve_tube']
remove = ns17['ns16']['ns15']['ns14']['ns13']['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
glass = bpy.data.objects['HERO_WINDSHIELD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

for n in ('HERO_P18_WINDSHIELD_FACE','HERO_P18_COWL_PANEL','HERO_P18_COWL_BREAK'):
    remove(n)
for side in (-1,1):
    for stem in ('HERO_P18_WINDSHIELD_EDGE_','HERO_P18_COWL_SHOULDER_'):
        remove(f'{stem}{side}')

# Replace the broad generic windshield read with a slightly narrower trapezoid:
# wide at the cowl, pulled inward at the header, with a modest rearward rake.
panel('HERO_P18_WINDSHIELD_FACE',[
    (.905,-.665,1.205),(.905,.665,1.205),
    (.590,.605,1.665),(.590,-.605,1.665)
],glass)

if LOD < 2:
    for side in (-1,1):
        curve_tube(f'HERO_P18_WINDSHIELD_EDGE_{side}',[
            (.905,side*.665,1.205),(.785,side*.646,1.385),
            (.675,side*.626,1.545),(.590,side*.605,1.665)
        ],.0065,black,1)

# Tacoma cowl/scuttle transition: hood terminates below the glass instead of
# visually running into it. The shoulder points also narrow the front cab in 3Q.
panel('HERO_P18_COWL_PANEL',[
    (.875,-.705,1.175),(.960,-.585,1.205),(.960,.585,1.205),
    (.875,.705,1.175),(.770,.620,1.145),(.770,-.620,1.145)
],paint)
curve_tube('HERO_P18_COWL_BREAK',[(.790,-.615,1.158),(.835,0,1.178),(.790,.615,1.158)],.005,black,1)

# Small painted shoulder breaks at the hood/cab corners reduce the old boxy
# slab-side transition while preserving the base FBX-derived door structure.
if LOD < 2:
    for side in (-1,1):
        curve_tube(f'HERO_P18_COWL_SHOULDER_{side}',[
            (.805,side*.615,1.155),(.900,side*.690,1.185),
            (1.055,side*.720,1.190)
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
print('[TPG TACOMA] quality patch18 complete: narrower raked windshield, defined cowl/scuttle and cleaner hood-to-cab shoulders; DCS mechanics untouched')
