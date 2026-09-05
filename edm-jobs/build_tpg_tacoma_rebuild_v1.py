import runpy
import math
import os
import bpy
from mathutils import Vector

# CLEAN REBUILD TACTIC
# --------------------
# Start from patch4 only: this is the proven FBX wheel/animation/material baseline
# with arg 8 wheel roll, arg 9 front steering, official ED materials and the
# original Tacoma FBX wheel geometry. Do NOT inherit patch5..patch28 body fixes.
# Those incremental overlays are intentionally abandoned here.
ns = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch4.py', run_name='__main__')
M = ns['M']
LOD = ns['LOD']
box = ns['box']
cyl = ns['cyl']
torus = ns['torus']
DESTROYED = os.environ.get('TPG_TACOMA_DESTROYED', '0') == '1'

# Reference frame is tied to the real DCLB wheelbase already proven by the rig:
# front axle +1.7855 m, rear axle -1.7855 m => 3.571 m / 140.6 in.
# Target overall body length ~5.73 m, width ~1.89 m. The user's concept sheet is
# the visual reference for cab rake, long-bed topper, stock 2016 fascia and
# custom rack/lights/sliders/rear bumper.


def remove_obj(o):
    try:
        bpy.data.objects.remove(o, do_unlink=True)
    except Exception:
        pass


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            remove_obj(o)


def mesh_obj(name, verts, faces, mat=None, smooth=True, bevel=0.0):
    me = bpy.data.meshes.new(name + '_mesh')
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if mat:
        me.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if bevel > 0 and LOD < 2:
        md = o.modifiers.new('edge_soften', 'BEVEL')
        md.width = bevel
        md.segments = 3 if LOD == 0 else 1
        bpy.context.view_layer.objects.active = o
        try:
            bpy.ops.object.modifier_apply(modifier=md.name)
        except Exception:
            pass
    return o


def loft(name, sections, mat, bevel=0.0, cap=True):
    count = len(sections[0][1])
    verts = []
    for x, ring in sections:
        if len(ring) != count:
            raise RuntimeError(f'{name}: inconsistent loft section')
        verts.extend((x, y, z) for y, z in ring)
    faces = []
    for i in range(len(sections) - 1):
        a = i * count
        b = (i + 1) * count
        for j in range(count):
            k = (j + 1) % count
            faces.append((a+j, a+k, b+k, b+j))
    if cap:
        faces.append(tuple(range(count - 1, -1, -1)))
        off = (len(sections) - 1) * count
        faces.append(tuple(off + j for j in range(count)))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def prism_xz(name, profile, y_center, thickness, mat, bevel=0.0):
    y0 = y_center - thickness * .5
    y1 = y_center + thickness * .5
    verts = [(x,y0,z) for x,z in profile] + [(x,y1,z) for x,z in profile]
    n = len(profile)
    faces = [tuple(range(n-1,-1,-1)), tuple(n+i for i in range(n))]
    for i in range(n):
        j = (i+1) % n
        faces.append((i,j,n+j,n+i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def prism_yz(name, profile, x0, x1, mat, bevel=0.0):
    verts = [(x0,y,z) for y,z in profile] + [(x1,y,z) for y,z in profile]
    n = len(profile)
    faces = [tuple(range(n-1,-1,-1)), tuple(n+i for i in range(n))]
    for i in range(n):
        j = (i+1) % n
        faces.append((i,j,n+j,n+i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def panel3d(name, pts, mat, thickness=.010):
    a,b,c = map(Vector, pts[:3])
    normal = (b-a).cross(c-a).normalized() * (thickness*.5)
    front = [tuple(Vector(p)+normal) for p in pts]
    back = [tuple(Vector(p)-normal) for p in pts]
    verts = front + back
    n = len(pts)
    faces = [tuple(range(n)), tuple(range(2*n-1,n-1,-1))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,n+j,n+i))
    return mesh_obj(name, verts, faces, mat, True, .002 if LOD == 0 else 0.0)


def curve_tube(name, pts, radius, mat, resolution=2):
    cu = bpy.data.curves.new(name + '_curve', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = resolution if LOD == 0 else 1
    cu.resolution_u = 1
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts):
        p.co = (*co,1.0)
    o = bpy.data.objects.new(name,cu)
    bpy.context.collection.objects.link(o)
    cu.materials.append(mat)
    return o


def ellipse_tube(name, x, cy, cz, ry, rz, radius, mat, count=28):
    pts=[]
    for i in range(count+1):
        a=math.tau*i/count
        pts.append((x,cy+ry*math.cos(a),cz+rz*math.sin(a)))
    return curve_tube(name,pts,radius,mat,1)


def upper_arch(cx, zc, r, x_front, x_rear, count):
    pts=[]
    for i in range(count):
        x=x_front+(x_rear-x_front)*i/(count-1)
        q=max(0.0,r*r-(x-cx)*(x-cx))
        pts.append((x,zc+math.sqrt(q)))
    return pts

# ---------------------------------------------------------------------------
# RETIRE ALL LEGACY VISUAL BODY/ACCESSORY GEOMETRY FROM PATCH4
# Keep only the FBX wheel meshes/joints, TRD wheel-face children, collision and
# exporter scene infrastructure. This is the key tactical change: no stacked body.
# ---------------------------------------------------------------------------
for o in list(bpy.data.objects):
    n=o.name
    keep = (
        n.startswith('FBX_Cylinder') or
        n.startswith('TRD_RIM_') or n.startswith('TRD_HUB_') or
        n.startswith('TRD_SPOKE_') or n.startswith('TRD_LUG_') or
        n.startswith('COLLISION_') or n.endswith('_STEER') or n.endswith('_ROLL') or
        n.startswith('ARG_') or n.startswith('EDM_')
    )
    if keep:
        continue
    if n.startswith('FBX_') or n.startswith((
        'CAMPER_', 'RACK_', 'DITCH_', 'BLACK_OAK_', 'SLIDER_',
        'REAR_', 'RECOVERY_', 'FRONT_', 'TACOMA_BADGE_', 'TRD_BADGE_',
        'OFFROAD_', 'HERO_'
    )):
        remove_obj(o)

paint = M['burnt'] if DESTROYED else M['paint']
black = M['black']
metal = M['metal']
glass = M['glass']
lamp = M['lamp']
amber = M.get('aux_amber', M['amber'])
red = M['red']
aux_led = M.get('aux_led', lamp)

# ---------------------------------------------------------------------------
# ONE COHERENT BODY SYSTEM
# ---------------------------------------------------------------------------
# Lower cab volume: width and shoulder taper are continuous from front door to
# rear door. This replaces the former stack of skins/cheeks/crowns.
def lower_ring(hw=.90, shoulder=.84, zbottom=.55, zside=1.15, ztop=1.23):
    return [(-hw*.88,zbottom),(-hw,zbottom+.09),(-hw,zside),(-shoulder,ztop),
            (0,ztop+.015),(shoulder,ztop),(hw,zside),(hw,zbottom+.09),(hw*.88,zbottom)]

loft('R1_CAB_LOWER', [
    (-.90,lower_ring(.90,.82,.55,1.14,1.21)),
    (-.50,lower_ring(.92,.84,.55,1.16,1.23)),
    (.10, lower_ring(.93,.85,.55,1.17,1.24)),
    (.70, lower_ring(.91,.82,.55,1.15,1.22)),
    (.88, lower_ring(.87,.78,.55,1.12,1.19)),
], paint, .018)

# Front fenders with actual wheel-opening silhouette cut into the side profile.
arc_n = 18 if LOD == 0 else (12 if LOD == 1 else 8)
front_arc = upper_arch(1.7855,.405,.660,2.38,1.19,arc_n)
front_profile = [
    (.78,.56),(.78,1.18),(1.03,1.23),(1.40,1.27),(1.82,1.29),
    (2.18,1.25),(2.45,1.17),(2.62,1.07),(2.73,.91),(2.75,.64),
    (2.43,.58)
] + front_arc + [(1.10,.58),(.78,.56)]
for side in (-1,1):
    prism_xz(f'R1_FRONT_QUARTER_{side}', front_profile, side*.914, .080, paint, .022)

# Long-bed sides use the same wheel-opening logic and correctly preserve the
# 140.6-in DCLB wheelbase rather than visually shortening the bed.
rear_arc = upper_arch(-1.7855,.405,.660,-1.19,-2.38,arc_n)
rear_profile = [
    (-.90,.56),(-.90,1.20),(-1.08,1.23),(-2.82,1.23),(-3.04,1.18),
    (-3.06,.58),(-2.48,.58)
] + rear_arc + [(-1.10,.58),(-.90,.56)]
for side in (-1,1):
    prism_xz(f'R1_BED_SIDE_{side}', rear_profile, side*.914, .080, paint, .022)

# Tailgate and rear corner shoulders.
prism_yz('R1_TAILGATE', [(-.86,.59),(-.91,.66),(-.91,1.18),(-.82,1.23),
                         (.82,1.23),(.91,1.18),(.91,.66),(.86,.59)],
         -3.08,-3.02,paint,.014)

# Hood: broad muscular third-gen crown, lower leading edge, and real side drop.
def hood_ring(hw,zedge,zcrown,zbottom):
    return [(-hw,zbottom),(-hw,zedge),(-hw*.72,zedge+.025),(-hw*.35,zcrown-.012),
            (0,zcrown),(hw*.35,zcrown-.012),(hw*.72,zedge+.025),(hw,zedge),(hw,zbottom)]
loft('R1_HOOD', [
    (.78,hood_ring(.79,1.155,1.205,1.105)),
    (1.20,hood_ring(.84,1.185,1.245,1.105)),
    (1.72,hood_ring(.86,1.195,1.255,1.095)),
    (2.18,hood_ring(.82,1.165,1.225,1.065)),
    (2.48,hood_ring(.72,1.105,1.165,1.030)),
],paint,.018)

# Cab roof/greenhouse: raked windshield, nearly level roof, substantial rear
# door glass and a slightly forward-raked C pillar as shown in the reference.
def roof_ring(hw,zbase,zedge,zshoulder,crown):
    return [(-hw,zbase),(-hw,zedge),(-hw*.72,zshoulder),(-hw*.36,crown-.012),
            (0,crown),(hw*.36,crown-.012),(hw*.72,zshoulder),(hw,zedge),(hw,zbase)]
loft('R1_CAB_ROOF', [
    (-.88,roof_ring(.66,1.55,1.66,1.75,1.785)),
    (-.70,roof_ring(.73,1.56,1.70,1.78,1.815)),
    (-.05,roof_ring(.75,1.56,1.71,1.79,1.825)),
    (.38, roof_ring(.73,1.55,1.69,1.77,1.805)),
    (.53, roof_ring(.65,1.53,1.64,1.72,1.760)),
],paint,.016)

panel3d('R1_WINDSHIELD',[(.86,-.82,1.18),(.86,.82,1.18),(.52,.65,1.69),(.52,-.65,1.69)],glass,.012)
panel3d('R1_REAR_CAB_GLASS',[(-.90,.66,1.21),(-.90,-.66,1.21),(-.86,-.62,1.65),(-.86,.62,1.65)],glass,.012)

for side in (-1,1):
    yb=side*.936
    # front side glass: more upright and rectangular than the rejected wedge shape
    panel3d(f'R1_FRONT_GLASS_{side}',[(.80,yb,1.20),(.05,yb,1.20),(.07,side*.735,1.66),(.50,side*.665,1.69)],glass,.010)
    panel3d(f'R1_REAR_GLASS_{side}',[(.01,yb,1.20),(-.78,yb,1.21),(-.84,side*.705,1.64),(.05,side*.735,1.66)],glass,.010)
    curve_tube(f'R1_A_PILLAR_{side}',[(.83,side*.93,1.17),(.50,side*.67,1.71)],.024,paint,2)
    curve_tube(f'R1_B_PILLAR_{side}',[(.03,side*.94,1.19),(.06,side*.74,1.68)],.026,black,1)
    curve_tube(f'R1_C_PILLAR_{side}',[(-.80,side*.94,1.20),(-.86,side*.70,1.66)],.028,paint,2)
    curve_tube(f'R1_WINDOW_SILL_{side}',[(-.80,side*.945,1.195),(.81,side*.945,1.188)],.013,black,1)

# Long-bed paint-matched camper shell. The cap sits just below cab crown, has a
# mild roof crown, forward rake and rear pinch rather than a rectangular van box.
def cap_ring(hw,zbottom,zside,zshoulder,zcrown):
    return [(-hw,zbottom),(-hw,zside),(-hw*.72,zshoulder),(-hw*.32,zcrown-.010),
            (0,zcrown),(hw*.32,zcrown-.010),(hw*.72,zshoulder),(hw,zside),(hw,zbottom)]
loft('R1_TOPPER', [
    (-3.01,cap_ring(.76,1.18,1.48,1.60,1.655)),
    (-2.82,cap_ring(.81,1.18,1.53,1.65,1.700)),
    (-1.22,cap_ring(.82,1.18,1.54,1.66,1.710)),
    (-1.01,cap_ring(.76,1.18,1.48,1.60,1.665)),
],paint,.018)
for side in (-1,1):
    panel3d(f'R1_TOPPER_GLASS_{side}',[
        (-2.78,side*.823,1.30),(-1.20,side*.823,1.30),(-1.08,side*.760,1.58),
        (-1.28,side*.735,1.63),(-2.69,side*.745,1.62),(-2.86,side*.760,1.53)
    ],glass,.010)
panel3d('R1_TOPPER_REAR_GLASS',[(-3.018,-.67,1.29),(-3.018,.67,1.29),
                                (-3.018,.60,1.59),(-3.018,-.60,1.59)],glass,.010)

# ---------------------------------------------------------------------------
# 2016 TACOMA FRONT FACE - ONE SYSTEM, NOT STACKED PATCHES
# ---------------------------------------------------------------------------
# Painted fascia bridge behind lamp/grille line.
prism_yz('R1_FRONT_FASCIA',[(-.94,.61),(-.94,1.02),(-.82,1.14),(-.66,1.20),
                            (.66,1.20),(.82,1.14),(.94,1.02),(.94,.61)],
         2.55,2.63,paint,.014)

# Recessed stock-like hex grille.
outer=[(-.66,1.16),(-.73,1.08),(-.70,.82),(-.58,.75),(.58,.75),(.70,.82),(.73,1.08),(.66,1.16)]
inner=[(-.56,1.10),(-.62,1.03),(-.60,.86),(-.50,.80),(.50,.80),(.60,.86),(.62,1.03),(.56,1.10)]
# simple outer painted frame as a shallow plate + smaller black insert
prism_yz('R1_GRILLE_FRAME',outer,2.62,2.68,paint,.008)
prism_yz('R1_GRILLE_BLACK',inner,2.675,2.695,black,.004)
if LOD < 2:
    for z in (.895,1.005):
        curve_tube(f'R1_GRILLE_BAR_{z}',[(2.700,-.51,z),(2.700,.51,z)],.0045,metal,1)
    ellipse_tube('R1_TOYOTA_OUTER',2.707,0,.95,.088,.054,.0065,metal,26 if LOD==0 else 18)
    ellipse_tube('R1_TOYOTA_INNER',2.709,0,.95,.043,.040,.004,metal,22 if LOD==0 else 16)

# Slim high-mounted lamps swept into the front fenders.
for side in (-1,1):
    s=side
    housing=[(s*.58,1.125),(s*.67,1.14),(s*.82,1.12),(s*.92,1.075),
             (s*.95,1.025),(s*.89,.99),(s*.67,1.00),(s*.59,1.045)]
    lensp=[(s*.60,1.11),(s*.68,1.125),(s*.80,1.108),(s*.89,1.070),
           (s*.92,1.032),(s*.87,1.006),(s*.69,1.015),(s*.61,1.052)]
    prism_yz(f'R1_LAMP_HOUSING_{side}',housing,2.64,2.69,black,.004)
    prism_yz(f'R1_HEADLAMP_{side}',lensp,2.69,2.704,lamp,.003)
    prism_yz(f'R1_AMBER_{side}',[(s*.88,1.073),(s*.925,1.052),(s*.93,1.025),(s*.89,1.01),(s*.86,1.027)],2.704,2.710,amber,.002)
    if LOD == 0:
        for idx,(yy,zz,rr) in enumerate(((.70,1.065,.032),(.79,1.055,.023))):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=rr,depth=.008,
                                               location=(2.712,s*yy,zz),rotation=(0,math.pi/2,0))
            p=bpy.context.object;p.name=f'R1_PROJECTOR_{side}_{idx}';p.data.materials.append(lamp)

# Painted bumper corners + black center lower opening and compact round fogs.
for side in (-1,1):
    s=side
    prism_yz(f'R1_BUMPER_CORNER_{side}',[
        (s*.94,.58),(s*.95,.69),(s*.90,.82),(s*.82,.91),
        (s*.70,.92),(s*.63,.82),(s*.67,.68),(s*.79,.59)
    ],2.59,2.68,paint,.012)
    prism_yz(f'R1_FOG_POCKET_{side}',[(s*.72,.60),(s*.84,.60),(s*.86,.65),(s*.83,.72),(s*.73,.73),(s*.69,.67)],2.675,2.698,black,.004)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24 if LOD==0 else 14,radius=.043,depth=.010,
                                       location=(2.704,s*.78,.66),rotation=(0,math.pi/2,0))
    f=bpy.context.object;f.name=f'R1_FOG_{side}';f.data.materials.append(lamp)
prism_yz('R1_LOWER_OPENING',[(-.60,.71),(-.68,.66),(-.64,.54),(.64,.54),(.68,.66),(.60,.71)],2.65,2.70,black,.005)
prism_yz('R1_LOWER_LIP',[(-.68,.53),(-.72,.50),(-.64,.47),(.64,.47),(.72,.50),(.68,.53)],2.62,2.68,paint,.006)
prism_yz('R1_LED_BAR',[(-.38,.635),(-.38,.600),(.38,.600),(.38,.635)],2.700,2.714,aux_led,.002)

# Subtle black wheel-arch flares, front and rear.
for side in (-1,1):
    s=side
    for tag,cx in (('F',1.7855),('R',-1.7855)):
        pts=[]
        for i in range(25 if LOD==0 else 15):
            a=math.radians(12+(156*i/((25 if LOD==0 else 15)-1)))
            pts.append((cx+.675*math.cos(a),s*.958,.405+.675*math.sin(a)))
        curve_tube(f'R1_FLARE_{tag}_{side}',pts,.026 if LOD==0 else .022,black,2)

# Vertical rear lamps at the bed corners.
for side in (-1,1):
    s=side
    prism_yz(f'R1_TAILLAMP_{side}',[(s*.82,.72),(s*.91,.74),(s*.91,1.14),(s*.82,1.18)],-3.10,-3.045,red,.006)

# ---------------------------------------------------------------------------
# USER'S VISIBLE CUSTOM EQUIPMENT - REBUILT CLEANLY AFTER BODY ACCEPTANCE LAYER
# ---------------------------------------------------------------------------
# One low-profile cab rack/platform.
for side in (-1,1):
    box(f'R1_RACK_RAIL_{side}',(-.05,side*.58,1.845),(1.16,.045,.045),black,.008)
    for x in (-.48,.38):
        box(f'R1_RACK_FOOT_{side}_{x}',(x,side*.56,1.795),(.09,.055,.075),black,.006)
for i,x in enumerate((-.50,-.27,-.04,.19,.42)):
    box(f'R1_RACK_BAR_{i}',(x,0,1.845),(.035,1.18,.025),black,.004)

# Square Black Oak-style ditch lights at the cowl, kept compact.
for side in (-1,1):
    s=side
    box(f'R1_DITCH_{side}',(.98,s*.83,1.43),(.13,.13,.13),black,.014)
    if LOD==0:
        for dy in (-.028,.028):
            for dz in (-.028,.028):
                cyl(f'R1_DITCH_LED_{side}_{dy}_{dz}',(1.048,s*.83+dy,1.43+dz),.014,.006,aux_led,12,rot=(0,math.pi/2,0))

# Rock sliders close to the rocker, not hanging as a second running-board stack.
for side in (-1,1):
    s=side
    curve_tube(f'R1_SLIDER_OUTER_{side}',[(-1.00,s*.99,.47),(1.04,s*.99,.47)],.035,black,2)
    curve_tube(f'R1_SLIDER_INNER_{side}',[(-.96,s*.88,.46),(1.00,s*.88,.46)],.024,black,1)
    for x in (-.70,-.15,.40,.88):
        curve_tube(f'R1_SLIDER_BRACE_{side}_{x}',[(x,s*.86,.45),(x,s*.97,.47)],.016,black,1)

# Custom heavy rear bumper, visually independent from the tailgate/cap.
box('R1_REAR_BUMPER',(-3.16,0,.61),(.16,1.86,.20),black,.020)
for side in (-1,1):
    s=side
    box(f'R1_REAR_WING_{side}',(-3.14,s*.78,.66),(.18,.32,.23),black,.018)
    box(f'R1_REAR_AMBER_{side}',(-3.245,s*.55,.68),(.010,.18,.070),amber,.008)
    torus(f'R1_RECOVERY_{side}',(-3.24,s*.31,.49),.050,.012,black,rot=(0,math.pi/2,0))

# UV safety for generated meshes required by the ED material exporter.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons or len(obj.data.uv_layers):
        continue
    me=obj.data
    uv=me.uv_layers.new(name='UVMap')
    xs=[v.co.x for v in me.vertices];ys=[v.co.y for v in me.vertices]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
    dx=max(xmax-xmin,1e-6);dy=max(ymax-ymin,1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=((co.x-xmin)/dx,(co.y-ymin)/dy)
    me.uv_layers.active=uv

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] CLEAN REBUILD v1 complete: single coherent 2016 DCLB body/fascia/topper system on proven FBX wheel rig; patch5-28 visual stack abandoned')
