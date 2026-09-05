import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch16.
# Priority: double-cab greenhouse/cab crown and cab-to-topper silhouette so the
# long-bed truck reads as the user's 2016 Tacoma DCLB in side/front-3Q clay QA.
# DCS registration, 113 mph tuning, wheel args 8/9, LOD/destroyed structure,
# exporter pipeline and Mods/tech packaging are intentionally untouched.
ns16 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch16.py', run_name='__main__')
LOD = ns16['LOD']
mesh_obj = ns16['ns15']['ns14']['ns13']['mesh_obj']
curve_tube = ns16['ns15']['ns14']['ns13']['curve_tube']
remove = ns16['ns15']['ns14']['ns13']['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)


def loft_sections(name, sections, mat, bevel=0.0):
    verts=[]
    n=len(sections[0][1])
    for x, ring in sections:
        verts.extend((x,y,z) for y,z in ring)
    faces=[tuple(range(n-1,-1,-1)), tuple((len(sections)-1)*n+i for i in range(n))]
    for s in range(len(sections)-1):
        a=s*n; b=(s+1)*n
        for i in range(n):
            j=(i+1)%n
            faces.append((a+i,a+j,b+j,b+i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


paint=bpy.data.objects['HERO_HOOD'].data.materials[0]
glass=bpy.data.objects['HERO_WINDSHIELD'].data.materials[0]
black=bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

for n in ('HERO_P17_CAB_CROWN','HERO_P17_WINDSHIELD_HEADER','HERO_P17_REAR_ROOF_BREAK'):
    remove(n)
for side in (-1,1):
    for stem in ('HERO_P17_ROOF_EDGE_','HERO_P17_A_PILLAR_SWEEP_','HERO_P17_REAR_CAB_SWEEP_'):
        remove(f'{stem}{side}')

# Low, rounded roof crown spanning the true double-cab length.  Earlier bodies
# read too slab-sided in clay; this adds the subtle center crown and narrower
# roof shoulders visible on a Tacoma without replacing the proven base shell.
def cab_ring(hw, lower, shoulder, crown):
    return [(-hw,lower),(-hw*.94,shoulder),(-hw*.62,crown-.020),(0,crown),
            (hw*.62,crown-.020),(hw*.94,shoulder),(hw,lower)]

loft_sections('HERO_P17_CAB_CROWN',[
    (-.955,cab_ring(.700,1.605,1.690,1.755)),
    (-.720,cab_ring(.735,1.610,1.700,1.770)),
    (.180,cab_ring(.742,1.610,1.705,1.776)),
    (.610,cab_ring(.705,1.595,1.685,1.755)),
],paint,.010)

# Thin dark roof-edge reveals make the crown legible in clay and visually pull
# the side glass inward instead of leaving a generic vertical greenhouse.
if LOD < 2:
    for side in (-1,1):
        curve_tube(f'HERO_P17_ROOF_EDGE_{side}',[
            (-.930,side*.690,1.690),(-.650,side*.720,1.708),
            (.170,side*.725,1.712),(.585,side*.690,1.690)
        ],.0045,black,1)

# A-pillars sweep rearward into the roof rather than reading as upright posts.
# This is deliberately a narrow visual seam, not a new structural pillar.
if LOD < 2:
    for side in (-1,1):
        curve_tube(f'HERO_P17_A_PILLAR_SWEEP_{side}',[
            (.875,side*.645,1.205),(.760,side*.690,1.395),
            (.640,side*.700,1.575),(.555,side*.680,1.690)
        ],.006,black,1)

# Rear cab wall/top break: establish the short painted shoulder between the rear
# door glass and topper. This prevents cab and cap from merging into one wagon.
for side in (-1,1):
    if LOD < 2:
        curve_tube(f'HERO_P17_REAR_CAB_SWEEP_{side}',[
            (-.930,side*.685,1.300),(-.955,side*.695,1.490),(-.950,side*.675,1.655)
        ],.0055,black,1)
curve_tube('HERO_P17_REAR_ROOF_BREAK',[(-.965,-.640,1.660),(-.972,0,1.705),(-.965,.640,1.660)],.0055,black,1)

# Subtle windshield header follows the crown arc, giving front/front-3Q views a
# narrower Tacoma cab top rather than a broad rectangular roof face.
curve_tube('HERO_P17_WINDSHIELD_HEADER',[(.575,-.620,1.665),(.610,0,1.730),(.575,.620,1.665)],.006,black,1)

# UV safety for official ED material export.
for obj in list(bpy.context.scene.objects):
    if obj.type!='MESH' or not obj.data.polygons or len(obj.data.uv_layers):
        continue
    me=obj.data
    uv=me.uv_layers.new(name='UVMap')
    xs=[v.co.x for v in me.vertices]; ys=[v.co.y for v in me.vertices]
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
    dx=max(xmax-xmin,1e-6); dy=max(ymax-ymin,1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=((co.x-xmin)/dx,(co.y-ymin)/dy)
    me.uv_layers.active=uv

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch17 complete: rounded double-cab crown, swept A-pillar/roof-edge cues and cleaner rear cab/topper break; DCS mechanics untouched')
