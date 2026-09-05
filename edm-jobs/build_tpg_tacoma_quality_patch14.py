import runpy
import math
import bpy

# Narrow front-identity pass on patch13. Corrected clay QA showed the grille
# proportions are now credible, but the lamp/fog solids still protrude like
# blocks. Make those elements shallow and integrated, and add the characteristic
# painted brow that ties the 2016 Tacoma hood, grille and lamps together.
# No DCS mechanics, collision, tuning, wheel animation, LOD/damage structure,
# exporter or packaging changes are made here.
ns13 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch13.py', run_name='__main__')
LOD = ns13['LOD']
mesh_obj = ns13['mesh_obj']
curve_tube = ns13['curve_tube']
remove = ns13['remove']


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def prism_yz(name, profile, x_center, thickness, mat, bevel=0.0):
    x0=x_center-thickness*.5; x1=x_center+thickness*.5
    verts=[(x0,y,z) for y,z in profile]+[(x1,y,z) for y,z in profile]
    n=len(profile)
    faces=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,n+j,n+i))
    return mesh_obj(name,verts,faces,mat,True,bevel)


def ellipse_tube(name,x,cy,cz,ry,rz,radius,mat,count=30):
    pts=[]
    for i in range(count+1):
        a=math.tau*i/count
        pts.append((x,cy+ry*math.cos(a),cz+rz*math.sin(a)))
    return curve_tube(name,pts,radius,mat,1)


paint=bpy.data.objects['HERO_HOOD'].data.materials[0]
black=bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]
lamp=bpy.data.objects['HERO_HEADLAMP_1'].data.materials[0]
amber=bpy.data.objects['HERO_AMBER_MARKER_1'].data.materials[0]
metal_obj=bpy.data.objects.get('HERO_GRILLE_SLAT_0')
metal=metal_obj.data.materials[0] if metal_obj and metal_obj.data.materials else black

# Remove only patch13 lamp/fog/bumper-corner surfaces that need integration.
for n in ('HERO_GRILLE_BROW','HERO_FRONT_BUMPER_WING_-1','HERO_FRONT_BUMPER_WING_1'):
    remove(n)
for pref in ('HERO_HEADLAMP_','HERO_AMBER_MARKER_','HERO_FOG_'):
    remove_prefix(pref)

# Painted upper brow: a thin shallow strip behind the grille/lamp line. It closes
# the visual gap between hood and fascia without masking the recessed grille.
prism_yz('HERO_GRILLE_BROW',[(-.590,1.125),(-.500,1.205),(.500,1.205),(.590,1.125)],2.676,.055,paint,.010)

# Flush lamp lenses with a slimmer 2016 Tacoma sweep. The inner edge follows the
# grille while the outside lifts slightly toward the fender.
left=[(-.955,.995),(-.915,1.075),(-.835,1.125),(-.575,1.115),(-.595,.995),(-.800,.965)]
right=[(.955,.995),(.915,1.075),(.835,1.125),(.575,1.115),(.595,.995),(.800,.965)]
prism_yz('HERO_HEADLAMP_-1',left,2.735,.012,lamp,.003)
prism_yz('HERO_HEADLAMP_1',right,2.735,.012,lamp,.003)

# Projector/reflector cues keep the lens from reading as an opaque polygon in clay.
if LOD < 2:
    for side in (-1,1):
        for idx,(yy,zz,rr) in enumerate(((.735,1.050,.040),(.645,1.045,.026))):
            y=side*yy
            bpy.ops.mesh.primitive_cylinder_add(vertices=24 if LOD==0 else 14,
                                               radius=rr,depth=.012,
                                               location=(2.747,y,zz),
                                               rotation=(0,math.pi/2,0))
            p=bpy.context.object
            p.name=f'HERO_HEADLAMP_PROJECTOR_{side}_{idx}'
            p.data.materials.append(lamp)
            ellipse_tube(f'HERO_HEADLAMP_RING_{side}_{idx}',2.754,y,zz,rr*1.18,rr*1.18,.0045,black,24 if LOD==0 else 16)

# Amber remains a narrow outside tip.
prism_yz('HERO_AMBER_MARKER_-1',[(-.958,1.000),(-.920,1.070),(-.875,1.095),(-.858,.982)],2.746,.010,amber,.002)
prism_yz('HERO_AMBER_MARKER_1',[(.958,1.000),(.920,1.070),(.875,1.095),(.858,.982)],2.746,.010,amber,.002)

# Smaller painted bumper shoulders tuck under the lamps rather than forming two
# vertical towers beside the grille.
prism_yz('HERO_FRONT_BUMPER_WING_-1',[(-.945,.600),(-.925,.760),(-.845,.875),(-.755,.910),(-.690,.825),(-.685,.635)],2.660,.060,paint,.012)
prism_yz('HERO_FRONT_BUMPER_WING_1',[(.945,.600),(.925,.760),(.845,.875),(.755,.910),(.690,.825),(.685,.635)],2.660,.060,paint,.012)

# Round fog lamps in compact recessed circular bezels; remove the polygonal
# pocket blocks entirely.
for side in (-1,1):
    y=side*.780; z=.655
    bpy.ops.mesh.primitive_cylinder_add(vertices=28 if LOD==0 else 16,
                                       radius=.070,depth=.014,
                                       location=(2.690,y,z),
                                       rotation=(0,math.pi/2,0))
    bezel=bpy.context.object
    bezel.name=f'HERO_FOG_BEZEL_{side}'
    bezel.data.materials.append(black)
    bpy.ops.mesh.primitive_cylinder_add(vertices=28 if LOD==0 else 16,
                                       radius=.048,depth=.016,
                                       location=(2.700,y,z),
                                       rotation=(0,math.pi/2,0))
    fog=bpy.context.object
    fog.name=f'HERO_FOG_{side}'
    fog.data.materials.append(lamp)
    ellipse_tube(f'HERO_FOG_RING_{side}',2.710,y,z,.055,.055,.004,metal,24 if LOD==0 else 16)

# Thin hood-leading seam helps front 3/4 read the hood as a separate stamped
# panel instead of one uninterrupted procedural slab.
remove('HERO_HOOD_LEADING_SEAM')
curve_tube('HERO_HOOD_LEADING_SEAM',[(2.42,-.64,1.075),(2.49,0,1.095),(2.42,.64,1.075)],.0055,black,1)

# Fill UVs only where generated meshes have none, preserving the official ED
# material export contract.
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
print('[TPG TACOMA] quality patch14 complete: flush swept lamps, projector cues, compact round fogs and painted grille brow; DCS mechanics untouched')
