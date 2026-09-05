import runpy
import bpy

# Geometry-only hero-body correction layered on export-green patch19.
# Priority: make the nose/hood read as the 2016 third-generation Tacoma shown in
# Toyota's launch photography: taller muscular hood, crisp outer shoulders, and
# a stronger clamp-shaped lower bumper relationship. DCS mechanics untouched.
ns19 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch19.py', run_name='__main__')
LOD = ns19['LOD']
mesh_obj = ns19['ns18']['ns17']['ns16']['ns15']['ns14']['ns13']['mesh_obj']
curve_tube = ns19['ns18']['ns17']['ns16']['ns15']['ns14']['ns13']['curve_tube']
remove = ns19['ns18']['ns17']['ns16']['ns15']['ns14']['ns13']['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)


def prism_yz(name, profile, x0, x1, mat, bevel=0.0):
    verts=[(x0,y,z) for y,z in profile]+[(x1,y,z) for y,z in profile]
    n=len(profile)
    faces=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,n+j,n+i))
    return mesh_obj(name,verts,faces,mat,True,bevel)

paint=bpy.data.objects['HERO_HOOD'].data.materials[0]
black=bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

# Retire patch16's flatter central dome/nose treatment. 2016 is the launch year
# of the third-generation body, whose hood is taller and more muscular with
# pronounced shoulders feeding the slim high-mounted lamps and hex grille.
for n in ('HERO_HOOD_POWER_DOME','HERO_TACOMA_NOSE_CAP',
          'HERO_P20_HOOD_CENTER','HERO_P20_NOSE_BACKING','HERO_P20_CLAMP_CHIN'):
    remove(n)
for side in (-1,1):
    for stem in ('HERO_P20_HOOD_SHOULDER_','HERO_P20_HOOD_EDGE_','HERO_P20_CLAMP_WING_'):
        remove(f'{stem}{side}')

# Taller stamped hood center: rear edge stays near the patch18 cowl while the
# front rises gently before dropping into the grille brow. Broad/low crown only.
panel('HERO_P20_HOOD_CENTER',[
    (.90,-.50,1.205),(1.55,-.53,1.225),(2.28,-.48,1.245),(2.50,-.36,1.205),
    (2.53,0.0,1.225),(2.50,.36,1.205),(2.28,.48,1.245),(1.55,.53,1.225),
    (.90,.50,1.205),(.82,0.0,1.225)
],paint)

# Outer hood/fender shoulders are the important third-gen silhouette cue: high
# near the cowl, crisp over the wheel flare, then pinched toward the lamps.
for side in (-1,1):
    s=side
    panel(f'HERO_P20_HOOD_SHOULDER_{side}',[
        (.86,s*.50,1.205),(1.30,s*.67,1.205),(1.90,s*.73,1.205),
        (2.34,s*.67,1.185),(2.50,s*.55,1.155),(2.28,s*.48,1.245),
        (1.55,s*.53,1.225)
    ],paint)
    if LOD < 2:
        curve_tube(f'HERO_P20_HOOD_EDGE_{side}',[
            (.88,s*.515,1.212),(1.35,s*.675,1.212),(1.92,s*.735,1.210),
            (2.34,s*.675,1.188),(2.49,s*.555,1.160)
        ],.0048,black,1)

# Shallow painted backing immediately behind the fascia gives the upper grille
# and lamps a body-integrated face instead of the old flat generic nose wall.
prism_yz('HERO_P20_NOSE_BACKING',[
    (-.68,.94),(-.63,1.10),(-.50,1.205),(0,1.245),(.50,1.205),
    (.63,1.10),(.68,.94),(.61,.88),(-.61,.88)
],2.50,2.565,paint,.010)

# Third-gen clamp-shaped bumper silhouette. These are restrained body surfaces,
# not accessory blocks, and sit behind the existing grille/fog/lamp detail.
for side in (-1,1):
    s=side
    prism_yz(f'HERO_P20_CLAMP_WING_{side}',[
        (s*.96,.58),(s*.94,.74),(s*.86,.87),(s*.72,.91),
        (s*.64,.82),(s*.66,.67),(s*.78,.58)
    ],2.58,2.655,paint,.010)
prism_yz('HERO_P20_CLAMP_CHIN',[
    (-.62,.53),(-.72,.59),(-.66,.69),(0,.72),(.66,.69),(.72,.59),(.62,.53)
],2.59,2.665,paint,.010)

# UV safety for official ED exporter.
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
print('[TPG TACOMA] quality patch20 complete: corrected 2016 third-gen hood shoulders, taller muscular hood and clamp-bumper body silhouette; DCS mechanics untouched')
