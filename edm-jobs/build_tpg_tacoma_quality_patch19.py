import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch18.
# Priority: long-bed topper rear/roof silhouette and cab-to-cap proportion in
# side and rear-3Q clay QA. Preserve all proven DCS mechanics and packaging.
ns18 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch18.py', run_name='__main__')
LOD = ns18['LOD']
mesh_obj = ns18['ns17']['ns16']['ns15']['ns14']['ns13']['mesh_obj']
curve_tube = ns18['ns17']['ns16']['ns15']['ns14']['ns13']['curve_tube']
remove = ns18['ns17']['ns16']['ns15']['ns14']['ns13']['remove']


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def loft_sections(name, sections, mat, bevel=0.0):
    verts=[]
    ring_n=len(sections[0][1])
    for x, ring in sections:
        verts.extend((x,y,z) for y,z in ring)
    faces=[tuple(range(ring_n-1,-1,-1))]
    off=(len(sections)-1)*ring_n
    faces.append(tuple(off+i for i in range(ring_n)))
    for s in range(len(sections)-1):
        a=s*ring_n; b=(s+1)*ring_n
        for i in range(ring_n):
            j=(i+1)%ring_n
            faces.append((a+i,a+j,b+j,b+i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint=bpy.data.objects['HERO_HOOD'].data.materials[0]
glass=bpy.data.objects['HERO_WINDSHIELD'].data.materials[0]
black=bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

# Replace patch15's still-bulky cap with a slightly lower roof crown and more
# deliberate long-bed taper. The front face remains close to the cab roofline,
# while the rear shoulder pinches inward to avoid a generic square camper read.
remove('HERO_CAMPER_SHELL')
remove('HERO_CAMPER_REAR_GLASS')
for pref in ('HERO_CAMPER_SIDE_GLASS_','HERO_CAMPER_TOP_FRAME_',
             'HERO_CAMPER_BOTTOM_FRAME_','HERO_CAMPER_FRONT_FRAME_',
             'HERO_CAMPER_REAR_FRAME_','HERO_CAMPER_DIVIDER_'):
    remove_prefix(pref)


def cap_ring(hw, bottom, belt, shoulder, crown):
    return [(-hw,bottom),(-hw,belt),(-hw*.80,shoulder),(-hw*.46,crown-.020),
            (0,crown),(hw*.46,crown-.020),(hw*.80,shoulder),(hw,belt),(hw,bottom)]

loft_sections('HERO_CAMPER_SHELL',[
    (-3.030, cap_ring(.720,1.180,1.485,1.625,1.690)),
    (-2.860, cap_ring(.775,1.180,1.545,1.675,1.735)),
    (-1.420, cap_ring(.790,1.180,1.555,1.688,1.745)),
    (-1.180, cap_ring(.755,1.180,1.525,1.660,1.730)),
    (-1.040, cap_ring(.705,1.180,1.490,1.625,1.700)),
],paint,.009)

# Side glazing follows the new taper with a thicker painted roof perimeter.
for side in (-1,1):
    panel(f'HERO_CAMPER_SIDE_GLASS_{side}',[
        (-2.820,side*.777,1.295),(-1.360,side*.790,1.295),
        (-1.205,side*.748,1.642),(-1.285,side*.760,1.682),
        (-2.735,side*.748,1.660)
    ],glass)
    if LOD < 2:
        curve_tube(f'HERO_CAMPER_TOP_FRAME_{side}',[
            (-2.735,side*.758,1.674),(-1.285,side*.770,1.696),(-1.190,side*.752,1.650)
        ],.010,black,1)
        curve_tube(f'HERO_CAMPER_BOTTOM_FRAME_{side}',[
            (-2.820,side*.784,1.286),(-1.360,side*.796,1.286)
        ],.011,black,1)
        curve_tube(f'HERO_CAMPER_FRONT_FRAME_{side}',[
            (-1.360,side*.796,1.286),(-1.190,side*.752,1.650)
        ],.011,black,1)
        curve_tube(f'HERO_CAMPER_REAR_FRAME_{side}',[
            (-2.820,side*.784,1.286),(-2.735,side*.758,1.674)
        ],.011,black,1)
        curve_tube(f'HERO_CAMPER_DIVIDER_{side}',[
            (-1.965,side*.790,1.288),(-1.955,side*.760,1.688)
        ],.0085,black,1)

# Rear glass is narrowed at the top and inset from the shell shoulders, giving
# the cap a curved/tapered rear read in rear-3Q instead of a flat vertical box.
panel('HERO_CAMPER_REAR_GLASS',[
    (-3.036,-.612,1.292),(-3.036,.612,1.292),
    (-3.000,.540,1.638),(-3.000,-.540,1.638)
],glass)
if LOD < 2:
    curve_tube('HERO_P19_REAR_GLASS_TOP',[(-3.002,-.540,1.646),(-3.004,0,1.662),(-3.002,.540,1.646)],.010,black,1)

# Refine the visible cab-cap separation so the topper reads as a distinct bed
# accessory while keeping the long-bed shell close enough to the cab.
for side in (-1,1):
    remove(f'HERO_CAP_CAB_GAP_{side}')
    curve_tube(f'HERO_CAP_CAB_GAP_{side}',[
        (-1.045,side*.675,1.628),(-.985,side*.680,1.650),(-.945,side*.680,1.662)
    ],.0065,black,1)

# UV safety for all newly generated visible meshes.
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
print('[TPG TACOMA] quality patch19 complete: lower crowned tapered topper, narrower rear glazing and cleaner cab-cap separation; DCS mechanics untouched')
