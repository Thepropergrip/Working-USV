import runpy
import math
import bpy

# Front-fascia recognition correction layered on the export-green patch12.
# The corrected collision-free clay QA showed patch12's cab/topper silhouette is
# materially better, but the nose still read too armored: lamps too tall, grille
# bars too dominant, bumper/fog geometry too massive.  This pass changes only
# visible front-clip geometry. DCS mechanics, collision, LOD/destroyed behavior,
# official exporter and package layout remain untouched.
ns12 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch12.py', run_name='__main__')
LOD = ns12['LOD']
mesh_obj = ns12['mesh_obj']
curve_tube = ns12['curve_tube']
remove = ns12['remove']


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def prism_yz(name, profile, x_center, thickness, mat, bevel=0.0):
    x0 = x_center - thickness * 0.5
    x1 = x_center + thickness * 0.5
    verts = [(x0,y,z) for y,z in profile] + [(x1,y,z) for y,z in profile]
    n = len(profile)
    faces = [tuple(range(n-1,-1,-1)), tuple(n+i for i in range(n))]
    for i in range(n):
        j = (i+1) % n
        faces.append((i,j,n+j,n+i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def ellipse_tube(name, x, cy, cz, ry, rz, radius, mat, count=36):
    pts=[]
    for i in range(count+1):
        a=math.tau*i/count
        pts.append((x,cy+ry*math.cos(a),cz+rz*math.sin(a)))
    return curve_tube(name,pts,radius,mat,1)


paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]
lamp = bpy.data.objects['HERO_HEADLAMP_1'].data.materials[0]
amber = bpy.data.objects['HERO_AMBER_MARKER_1'].data.materials[0]
metal_obj = bpy.data.objects.get('HERO_GRILLE_SLAT_0')
metal = metal_obj.data.materials[0] if metal_obj and metal_obj.data.materials else black

# Remove patch12 fascia as one visual system.
for n in ('HERO_GRILLE_FACE','HERO_LOWER_VALANCE','HERO_FRONT_BUMPER_CENTER'):
    remove(n)
for pref in ('HERO_GRILLE_','HERO_HEADLAMP_','HERO_AMBER_MARKER_',
             'HERO_FRONT_BUMPER_WING_','HERO_FOG_','HERO_TOYOTA_P13_'):
    remove_prefix(pref)

# 2016 Tacoma grille: lower and slightly narrower than patch12, inset rather
# than constructed as a thick cage. The outer polygon is only a shallow plate.
grille = [(-.575,.790),(-.650,.855),(-.625,1.060),(-.515,1.135),
          (.515,1.135),(.625,1.060),(.650,.855),(.575,.790)]
prism_yz('HERO_GRILLE_FACE', grille, 2.718, .022, black, .009)

# Three restrained horizontal bars survive clay QA without becoming the grille.
if LOD < 2:
    for i,z in enumerate((.855,.945,1.035)):
        half = .545 if i < 2 else .505
        curve_tube(f'HERO_GRILLE_SLAT_{i}',[(2.734,-half,z),(2.734,half,z)],.0065 if LOD==0 else .009,metal,1)

# Small raised Toyota oval at the center provides the unmistakable stock cue.
ellipse_tube('HERO_TOYOTA_P13_OUTER',2.741,0,.955,.110,.066,.009,metal,30 if LOD==0 else 20)
ellipse_tube('HERO_TOYOTA_P13_INNER',2.744,0,.955,.052,.050,.006,metal,26 if LOD==0 else 18)
curve_tube('HERO_TOYOTA_P13_BAR',[(2.746,-.075,.955),(2.746,.075,.955)],.0055,metal,1)

# Slim, broad headlamp housings. These are deliberately ~0.17 m tall rather
# than the patch12 ~0.26 m blocks and sit nearly flush with the grille plane.
left = [(-.950,.985),(-.910,1.085),(-.815,1.135),(-.565,1.125),(-.590,.985),(-.790,.955)]
right = [( .950,.985),( .910,1.085),( .815,1.135),( .565,1.125),( .590,.985),( .790,.955)]
prism_yz('HERO_HEADLAMP_-1',left,2.728,.022,lamp,.006)
prism_yz('HERO_HEADLAMP_1',right,2.728,.022,lamp,.006)
# Amber is only the outer tip, not a second block.
prism_yz('HERO_AMBER_MARKER_-1',[(-.955,.990),(-.915,1.075),(-.865,1.095),(-.850,.970)],2.741,.014,amber,.003)
prism_yz('HERO_AMBER_MARKER_1',[(.955,.990),(.915,1.075),(.865,1.095),(.850,.970)],2.741,.014,amber,.003)

# Body-colour bumper shoulders curve visually under the lamps and leave a clear
# break around the center grille, as on the stock third-gen nose.
prism_yz('HERO_FRONT_BUMPER_WING_-1',[(-.950,.585),(-.930,.770),(-.845,.900),(-.720,.930),(-.645,.805),(-.670,.620)],2.672,.078,paint,.014)
prism_yz('HERO_FRONT_BUMPER_WING_1',[(.950,.585),(.930,.770),(.845,.900),(.720,.930),(.645,.805),(.670,.620)],2.672,.078,paint,.014)
# Narrow painted bridge below grille; prevents the black center from becoming a
# single armored mask from grille to skid/LED-bar area.
prism_yz('HERO_FRONT_BUMPER_CENTER',[(-.610,.695),(-.670,.745),(.670,.745),(.610,.695)],2.668,.070,paint,.010)

# Compact black lower valance, significantly shorter than patch12.
prism_yz('HERO_LOWER_VALANCE',[(-.610,.505),(-.760,.565),(-.710,.675),(-.535,.700),(.535,.700),(.710,.675),(.760,.565),(.610,.505)],2.662,.070,black,.011)

# Round stock-position fog lamps in small black pockets instead of hexagonal
# armored bezels.
for side in (-1,1):
    # shallow black pocket
    prism_yz(f'HERO_FOG_POCKET_{side}',[
        (side*.790,.585),(side*.835,.615),(side*.835,.695),(side*.785,.725),(side*.720,.690),(side*.720,.615)
    ],2.690,.026,black,.006)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24 if LOD==0 else 14,
                                       radius=.052,depth=.018,
                                       location=(2.706,side*.775,.655),
                                       rotation=(0,math.pi/2,0))
    fog=bpy.context.object
    fog.name=f'HERO_FOG_{side}'
    fog.data.materials.append(lamp)
    ellipse_tube(f'HERO_FOG_RING_{side}',2.718,side*.775,.655,.065,.065,.006,black,24 if LOD==0 else 16)

# Keep the hood cues from patch10 but reduce their raised-tube effect so they
# read as sheet-metal creases rather than rails.
for o in list(bpy.data.objects):
    if o.name == 'HERO_HOOD_CENTER_CUE' or o.name.startswith('HERO_HOOD_CREASE_'):
        o.scale.y *= .70
        o.scale.z *= .70

# ED material exporter requires a UV channel on generated mesh objects.
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
print('[TPG TACOMA] quality patch13 complete: slimmer 2016 grille/headlamps, stock bumper break and round fog pockets; DCS mechanics untouched')
