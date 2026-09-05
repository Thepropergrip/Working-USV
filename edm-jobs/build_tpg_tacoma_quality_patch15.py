import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch14.
# Goal: make the long-bed shell and cab/topper transition read like the user's
# actual 2016 Tacoma rather than a box placed on the bed.  Preserve all DCS
# mechanics, wheel arguments, collision/LOD/destroyed structure, exporter and
# package layout by changing only generated visible geometry.
ns14 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch14.py', run_name='__main__')
LOD = ns14['LOD']
mesh_obj = ns14['ns13']['mesh_obj']
curve_tube = ns14['ns13']['curve_tube']
remove = ns14['ns13']['remove']


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def loft_sections(name, sections, mat, bevel=0.0):
    # sections: [(x, [(y,z), ...]), ...] with equal ring sizes.
    verts=[]
    ring_n=len(sections[0][1])
    for x, ring in sections:
        verts.extend((x,y,z) for y,z in ring)
    faces=[]
    # end caps
    faces.append(tuple(range(ring_n-1,-1,-1)))
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

# Rebuild the topper as a lightly crowned, tapered truck cap instead of a
# rectangular camper mass.  The cap sits just below the cab crown, has a softer
# front shoulder, slightly narrower roof, and a subtle rear taper.
remove('HERO_CAMPER_SHELL')
remove('HERO_CAMPER_REAR_GLASS')
for pref in ('HERO_CAMPER_SIDE_GLASS_','HERO_CAMPER_TOP_FRAME_',
             'HERO_CAMPER_BOTTOM_FRAME_','HERO_CAMPER_FRONT_FRAME_',
             'HERO_CAMPER_REAR_FRAME_','HERO_CAMPER_DIVIDER_'):
    remove_prefix(pref)


def cap_ring(hw, bottom, belt, shoulder, crown):
    return [(-hw,bottom),(-hw,belt),(-hw*.82,shoulder),(-hw*.48,crown-.018),
            (0,crown),(hw*.48,crown-.018),(hw*.82,shoulder),(hw,belt),(hw,bottom)]

loft_sections('HERO_CAMPER_SHELL', [
    (-3.015, cap_ring(.742,1.180,1.500,1.650,1.710)),
    (-2.895, cap_ring(.800,1.180,1.565,1.700,1.755)),
    (-1.300, cap_ring(.805,1.180,1.575,1.710,1.765)),
    (-1.095, cap_ring(.765,1.180,1.535,1.675,1.742)),
    (-1.020, cap_ring(.725,1.180,1.500,1.645,1.718)),
], paint, .010)

# Side glass follows the shell taper and leaves a visible painted perimeter.
for side in (-1,1):
    y=side*.808
    panel(f'HERO_CAMPER_SIDE_GLASS_{side}',[
        (-2.775,y,1.292),(-1.295,y,1.292),(-1.145,side*.755,1.662),
        (-1.225,side*.775,1.704),(-2.700,side*.778,1.684)
    ],glass)
    curve_tube(f'HERO_CAMPER_TOP_FRAME_{side}',[(-2.700,side*.790,1.700),(-1.225,side*.790,1.718),(-1.135,side*.765,1.670)],.010,black,1)
    curve_tube(f'HERO_CAMPER_BOTTOM_FRAME_{side}',[(-2.775,y,1.282),(-1.295,y,1.282)],.011,black,1)
    curve_tube(f'HERO_CAMPER_FRONT_FRAME_{side}',[(-1.295,y,1.282),(-1.135,side*.765,1.670)],.012,black,1)
    curve_tube(f'HERO_CAMPER_REAR_FRAME_{side}',[(-2.775,y,1.282),(-2.700,side*.790,1.700)],.012,black,1)
    curve_tube(f'HERO_CAMPER_DIVIDER_{side}',[(-1.950,y,1.286),(-1.940,side*.790,1.700)],.009,black,1)

panel('HERO_CAMPER_REAR_GLASS',[
    (-3.020,-.630,1.285),(-3.020,.630,1.285),
    (-2.985,.570,1.655),(-2.985,-.570,1.655)
],glass)

# Clean the cab-to-cap gap into one intentional shadow line. This makes the
# double-cab roof remain visually distinct while preventing the topper front
# wall from reading as a vertical billboard in side/front-3Q clay renders.
for side in (-1,1):
    remove(f'HERO_CAP_CAB_GAP_{side}')
    curve_tube(f'HERO_CAP_CAB_GAP_{side}',[(-1.030,side*.690,1.655),(-.955,side*.690,1.665)],.007,black,1)

# Subtle hood shoulder seams reinforce the stock Tacoma front clip without
# adding more fascia mass. They remain geometry cues in clay and disappear at
# the simplified LOD2.
for side in (-1,1):
    remove(f'HERO_HOOD_SHOULDER_{side}')
    if LOD < 2:
        curve_tube(f'HERO_HOOD_SHOULDER_{side}',[(1.18,side*.690,1.185),(1.88,side*.705,1.160),(2.38,side*.625,1.095)],.0045,black,1)

# ED material export requires UV channels on generated mesh geometry.
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
print('[TPG TACOMA] quality patch15 complete: tapered long-bed topper, cleaner cab-cap transition and hood shoulder silhouette; DCS mechanics untouched')
