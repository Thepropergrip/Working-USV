import runpy
import math
import bpy
from mathutils import Vector

# Geometry-only silhouette pass on the exporter-proven patch8 baseline.
# Preserve registration, wheel arguments, tuning, LOD/destroyed behavior and packaging.
runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch8.py', run_name='__main__')

LOD = int(__import__('os').environ.get('TPG_TACOMA_LOD', '0'))


def remove(name):
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)


def mesh_obj(name, verts, faces, mat, smooth=True, bevel=0.0):
    me = bpy.data.meshes.new(name + '_mesh')
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    if bevel > 0 and LOD < 2:
        mod = o.modifiers.new('edge_soften', 'BEVEL')
        mod.width = bevel
        mod.segments = 2 if LOD == 0 else 1
        bpy.context.view_layer.objects.active = o
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception:
            pass
    return o


def loft(name, sections, mat, bevel=0.0):
    n = len(sections[0][1])
    verts = []
    for x, ring in sections:
        verts.extend((x, y, z) for y, z in ring)
    faces = []
    for i in range(len(sections)-1):
        a, b = i*n, (i+1)*n
        for j in range(n):
            k = (j+1) % n
            faces.append((a+j, a+k, b+k, b+j))
    faces.append(tuple(range(n-1, -1, -1)))
    off = (len(sections)-1)*n
    faces.append(tuple(off+j for j in range(n)))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def panel(name, pts, mat, thickness=.012):
    a,b,c = map(Vector, pts[:3])
    normal = (b-a).cross(c-a).normalized() * (thickness*.5)
    front = [tuple(Vector(p)+normal) for p in pts]
    back = [tuple(Vector(p)-normal) for p in pts]
    verts = front + back
    m = len(pts)
    faces = [tuple(range(m)), tuple(range(2*m-1,m-1,-1))]
    for i in range(m):
        j=(i+1)%m
        faces.append((i,j,m+j,m+i))
    return mesh_obj(name, verts, faces, mat, True, .002 if LOD == 0 else 0.0)


def prism_xz(name, profile, y_center, thickness, mat, bevel=0.0):
    y0 = y_center - thickness * 0.5
    y1 = y_center + thickness * 0.5
    verts = [(x, y0, z) for x, z in profile] + [(x, y1, z) for x, z in profile]
    n = len(profile)
    faces = [tuple(range(n-1,-1,-1)), tuple(n+i for i in range(n))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,n+j,n+i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def curve_tube(name, pts, radius, mat, resolution=2):
    c = bpy.data.curves.new(name + '_curve', 'CURVE')
    c.dimensions = '3D'
    c.bevel_depth = radius
    c.bevel_resolution = resolution if LOD == 0 else 1
    c.resolution_u = 1
    s = c.splines.new('POLY')
    s.points.add(len(pts)-1)
    for p,co in zip(s.points,pts):
        p.co = (*co,1.0)
    o = bpy.data.objects.new(name,c)
    bpy.context.collection.objects.link(o)
    c.materials.append(mat)
    return o


paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
glass = bpy.data.objects['HERO_WINDSHIELD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

# Remove the previous greenhouse/front-clip pieces as a set so the new surfaces
# share one coherent 2016 Tacoma silhouette instead of layering over old planes.
for n in ('HERO_CAB_ROOF','HERO_WINDSHIELD','HERO_REAR_CAB_GLASS','HERO_HOOD',
          'HERO_CAMPER_SHELL','HERO_FRONT_FENDER_-1','HERO_FRONT_FENDER_1'):
    remove(n)
for side in (-1,1):
    for stem in ('HERO_FRONT_WINDOW_','HERO_REAR_WINDOW_','HERO_A_PILLAR_',
                 'HERO_B_PILLAR_','HERO_C_PILLAR_','HERO_WINDOW_SILL_'):
        remove(stem + str(side))

# Front fenders: preserve wheel opening and track, but pull the upper shoulder down
# and give the third-gen Tacoma nose a descending front edge rather than a tall slab.
def upper_arc_profile(cx, zc, r, x_front, x_rear, n=16):
    pts=[]
    for i in range(n):
        x=x_front+(x_rear-x_front)*i/(n-1)
        q=max(0.0,r*r-(x-cx)*(x-cx))
        pts.append((x,zc+math.sqrt(q)))
    return pts

front_arc = upper_arc_profile(1.7855,.405,.585,2.38,1.19,16 if LOD==0 else 10)
for side in (-1,1):
    profile=[(.70,.57),(.70,1.105),(1.02,1.155),(1.53,1.205),(2.02,1.195),
             (2.38,1.135),(2.63,1.035),(2.76,.84),(2.76,.57),(2.46,.57)] + front_arc + [(1.04,.57)]
    prism_xz(f'HERO_FRONT_FENDER_{side}',profile,side*.904,.082,paint,.024)

# Hood: longer central crown, lower leading edge and stronger outer-edge drop.
def hood_ring(width,zedge,zcrown,bottom):
    return [(-width,bottom),(-width,zedge),(-width*.68,zedge+.018),
            (-width*.34,zcrown-.010),(0,zcrown),(width*.34,zcrown-.010),
            (width*.68,zedge+.018),(width,zedge),(width,bottom)]
loft('HERO_HOOD',[
    (.70,hood_ring(.775,1.095,1.145,1.055)),
    (1.10,hood_ring(.825,1.125,1.185,1.055)),
    (1.70,hood_ring(.850,1.135,1.205,1.045)),
    (2.18,hood_ring(.825,1.105,1.175,1.015)),
    (2.50,hood_ring(.740,1.020,1.085,.975)),
],paint,.016)

# DCLB greenhouse. Longitudinal crown and taper are deliberately asymmetric:
# near-vertical rear cab wall, broad mid-roof and a distinctly raked windshield.
def roof_ring(hw,zbase,zedge,zshoulder,crown):
    return [(-hw,zbase),(-hw,zedge),(-hw*.68,zshoulder),(-hw*.32,crown-.012),
            (0,crown),(hw*.32,crown-.012),(hw*.68,zshoulder),(hw,zedge),(hw,zbase)]
loft('HERO_CAB_ROOF',[
    (-.92,roof_ring(.665,1.585,1.665,1.745,1.780)),
    (-.72,roof_ring(.735,1.590,1.700,1.775,1.810)),
    (-.05,roof_ring(.755,1.590,1.710,1.785,1.820)),
    (.37,roof_ring(.735,1.575,1.690,1.765,1.800)),
    (.54,roof_ring(.670,1.550,1.650,1.720,1.755)),
],paint,.014)

panel('HERO_WINDSHIELD',[(.86,-.825,1.145),(.86,.825,1.145),(.50,.665,1.690),(.50,-.665,1.690)],glass,.012)
panel('HERO_REAR_CAB_GLASS',[(-.905,.665,1.205),(-.905,-.665,1.205),(-.875,-.625,1.650),(-.875,.625,1.650)],glass,.012)

# Side glass and pillars follow the new windshield/crown, with the low rear-door
# roof step and slanted C-pillar visible in the user's double-cab photos.
for side in (-1,1):
    yb=side*.924
    yt=side*.735
    panel(f'HERO_FRONT_WINDOW_{side}',[(.79,yb,1.185),(.06,yb,1.185),(.08,yt,1.655),(.49,side*.675,1.690)],glass,.010)
    panel(f'HERO_REAR_WINDOW_{side}',[(.02,yb,1.185),(-.76,yb,1.205),(-.83,side*.705,1.625),(.05,yt,1.655)],glass,.010)
    curve_tube(f'HERO_A_PILLAR_{side}',[(.82,side*.925,1.16),(.49,side*.690,1.705)],.026,paint,2)
    curve_tube(f'HERO_B_PILLAR_{side}',[(.035,side*.928,1.18),(.065,side*.742,1.675)],.030,black,1)
    curve_tube(f'HERO_C_PILLAR_{side}',[(-.80,side*.925,1.19),(-.86,side*.705,1.655)],.032,paint,2)
    curve_tube(f'HERO_WINDOW_SILL_{side}',[(-.80,side*.932,1.188),(.81,side*.932,1.178)],.016,black,1)

# Topper: custom bed cap remains, but it now sits visibly below the cab crown,
# follows the long-bed shoulder, and has a mild forward rake instead of a van roof.
def topper_ring(hw,zbottom,zside,zshoulder,zcrown):
    return [(-hw,zbottom),(-hw,zside),(-hw*.70,zshoulder),(-hw*.30,zcrown-.010),
            (0,zcrown),(hw*.30,zcrown-.010),(hw*.70,zshoulder),(hw,zside),(hw,zbottom)]
loft('HERO_CAMPER_SHELL',[
    (-3.00,topper_ring(.770,1.175,1.465,1.610,1.655)),
    (-2.86,topper_ring(.815,1.175,1.505,1.650,1.700)),
    (-1.18,topper_ring(.820,1.175,1.520,1.665,1.715)),
    (-.98,topper_ring(.745,1.175,1.455,1.590,1.645)),
],paint,.018)

# Existing topper glass/frame accessories were positioned for the taller shell.
# Move only those visual pieces down slightly; no gameplay or export structure changes.
for obj in list(bpy.data.objects):
    if obj.name.startswith('HERO_CAMPER_SIDE_GLASS_') or obj.name.startswith('HERO_CAMPER_TOP_FRAME_') \
       or obj.name.startswith('HERO_CAMPER_FRONT_FRAME_') or obj.name.startswith('HERO_CAMPER_REAR_FRAME_') \
       or obj.name.startswith('HERO_CAMPER_DIVIDER_') or obj.name == 'HERO_CAMPER_REAR_GLASS':
        obj.location.z -= .055

# Patch8 UV guarantee must also cover the newly generated meshes.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons or len(obj.data.uv_layers):
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
print('[TPG TACOMA] quality patch9b complete: lower sculpted front clip, coherent raked DCLB greenhouse, lower long-bed topper; DCS mechanics untouched')
