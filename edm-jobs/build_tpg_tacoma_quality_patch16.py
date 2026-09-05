import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch15.
# Priority: sharpen the 2016 Tacoma front clip in clay views without touching
# DCS registration, tuning, animation arguments, LOD/destroyed structure,
# exporter, collision, or package layout.
ns15 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch15.py', run_name='__main__')
LOD = ns15['LOD']
mesh_obj = ns15['ns14']['ns13']['mesh_obj']
curve_tube = ns15['ns14']['ns13']['curve_tube']
remove = ns15['ns14']['ns13']['remove']


def prism_yz(name, profile, x0, x1, mat, bevel=0.0):
    verts=[(x0,y,z) for y,z in profile]+[(x1,y,z) for y,z in profile]
    n=len(profile)
    faces=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,n+j,n+i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint=bpy.data.objects['HERO_HOOD'].data.materials[0]
black=bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

# Replace any prior patch16 cues cleanly on rerun.
for n in (
    'HERO_TACOMA_NOSE_CAP','HERO_HOOD_POWER_DOME','HERO_LOWER_GRILLE_CHIN',
    'HERO_FRONT_FENDER_CHEEK_-1','HERO_FRONT_FENDER_CHEEK_1',
    'HERO_FENDER_ARCH_LIP_-1','HERO_FENDER_ARCH_LIP_1',
    'HERO_HOOD_CENTER_BREAK_-1','HERO_HOOD_CENTER_BREAK_1'):
    remove(n)

# Tacoma-specific nose: broad painted upper face with a slight forward rake.
# This reduces the generic flat-wall front and makes front/front-3Q clay views
# read as a second-gen Tacoma hood/fascia junction.
prism_yz('HERO_TACOMA_NOSE_CAP',[
    (-.650,1.090),(-.545,1.205),(0.0,1.245),(.545,1.205),(.650,1.090),
    (.615,.965),(0.0,.930),(-.615,.965)
],2.475,2.555,paint,.012)

# Low, wide hood center crown. Kept deliberately subtle so it changes the
# silhouette rather than looking like an aftermarket scoop.
panel('HERO_HOOD_POWER_DOME',[
    (1.15,-.34,1.205),(2.40,-.30,1.205),(2.50,0.0,1.235),
    (2.40,.30,1.205),(1.15,.34,1.205),(.92,0.0,1.225)
],paint)

# Pronounced front fender cheeks: the 2016 Tacoma carries visible shoulder mass
# over the front tires before pinching toward the lamps. This is one of the
# largest silhouette differences versus the rejected generic pickup body.
for side in (-1,1):
    y0=side*.825; y1=side*.925
    profile=[
        (side*.70,.78),(side*.79,.86),(side*.86,.98),(side*.88,1.10),
        (side*.80,1.18),(side*.68,1.20)
    ]
    prism_yz(f'HERO_FRONT_FENDER_CHEEK_{side}',profile,1.72,2.50,paint,.014)
    if LOD < 2:
        curve_tube(f'HERO_FENDER_ARCH_LIP_{side}',[
            (1.60,side*.875,.805),(1.72,side*.930,.925),(1.98,side*.955,1.055),
            (2.22,side*.925,1.090),(2.44,side*.850,1.055)
        ],.009,black,1)

# Hood break lines converge toward the grille instead of staying parallel; this
# gives the front clip the characteristic Tacoma taper in top/front-3Q views.
if LOD < 2:
    for side in (-1,1):
        curve_tube(f'HERO_HOOD_CENTER_BREAK_{side}',[
            (.95,side*.455,1.220),(1.65,side*.500,1.205),(2.30,side*.455,1.170),
            (2.48,side*.385,1.145)
        ],.0045,black,1)

# A shallow lower chin under the grille creates the stock stepped bumper read
# without reintroducing the bulky block geometry removed in patch14.
prism_yz('HERO_LOWER_GRILLE_CHIN',[
    (-.600,.655),(-.535,.805),(0,.835),(.535,.805),(.600,.655),
    (.505,.585),(-.505,.585)
],2.650,2.705,paint,.010)

# Maintain exporter UV requirements for every generated mesh.
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
print('[TPG TACOMA] quality patch16 complete: Tacoma nose rake, hood crown, front-fender shoulder mass and tapered hood breaks; DCS mechanics untouched')
