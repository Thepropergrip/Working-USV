import runpy
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

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
glass = bpy.data.objects['HERO_WINDSHIELD'].data.materials[0]

# 2016 Tacoma cab: longer DCLB roof, stronger windshield rake, tapered crown.
for n in ('HERO_CAB_ROOF','HERO_WINDSHIELD','HERO_REAR_CAB_GLASS'):
    remove(n)

def roof_ring(hw, zedge, zshoulder, crown):
    return [(-hw,1.56),(-hw,zedge),(-hw*.70,zshoulder),(0,crown),(hw*.70,zshoulder),(hw,zedge),(hw,1.56),(0,1.545)]

loft('HERO_CAB_ROOF', [
    (-.90, roof_ring(.70,1.69,1.79,1.825)),
    (-.54, roof_ring(.755,1.72,1.805,1.845)),
    (.15, roof_ring(.755,1.72,1.805,1.845)),
    (.50, roof_ring(.705,1.68,1.775,1.81)),
], paint, .016)
panel('HERO_WINDSHIELD', [(.86,-.82,1.17),(.86,.82,1.17),(.49,.70,1.705),(.49,-.70,1.705)], glass, .014)
panel('HERO_REAR_CAB_GLASS', [(-.89,.70,1.20),(-.89,-.70,1.20),(-.86,-.65,1.665),(-.86,.65,1.665)], glass, .014)

# Front clip: extend and taper the hood nose instead of ending as a short flat slab.
remove('HERO_HOOD')
def hood_ring(width, zedge, zcrown, bottom):
    return [(-width,bottom),(-width,zedge),(-width*.62,(zedge+zcrown)*.5),(0,zcrown),(width*.62,(zedge+zcrown)*.5),(width,zedge),(width,bottom)]
loft('HERO_HOOD', [
    (.72, hood_ring(.79,1.145,1.185,1.095)),
    (1.18, hood_ring(.845,1.178,1.228,1.105)),
    (1.82, hood_ring(.855,1.178,1.238,1.095)),
    (2.30, hood_ring(.805,1.115,1.175,1.035)),
    (2.49, hood_ring(.715,1.055,1.105,1.005)),
], paint, .018)

# Topper: lower, slightly narrower crown with near-vertical rear and a modest front rake.
remove('HERO_CAMPER_SHELL')
def topper_ring(hw, zbottom, zside, zshoulder, zcrown):
    return [(-hw,zbottom),(-hw,zside),(-hw*.78,zshoulder),(0,zcrown),(hw*.78,zshoulder),(hw,zside),(hw,zbottom),(0,zbottom-.02)]
loft('HERO_CAMPER_SHELL', [
    (-2.96, topper_ring(.79,1.17,1.49,1.65,1.705)),
    (-2.84, topper_ring(.835,1.17,1.55,1.71,1.765)),
    (-1.08, topper_ring(.835,1.17,1.57,1.73,1.78)),
    (-.93, topper_ring(.77,1.17,1.51,1.66,1.72)),
], paint, .022)

# Patch8 UV guarantee must also cover the newly generated meshes.
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
print('[TPG TACOMA] quality patch9 complete: DCLB cab rake/roof, tapered front clip, lower photo-match topper silhouette')
