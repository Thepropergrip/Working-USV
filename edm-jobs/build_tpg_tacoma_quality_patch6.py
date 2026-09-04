import runpy, math, os
import bpy
from mathutils import Vector

# Start from the proven single-scene / wheel-animation / DCS-export baseline.
ns = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch5.py', run_name='__main__')
M = ns['M']
LOD = ns['LOD']
DESTROYED = os.environ.get('TPG_TACOMA_DESTROYED', '0') == '1'

# ---------------------------------------------------------------------------
# HERO BODY REBUILD
# The supplied free low-poly FBX is retained for its validated four wheel meshes
# and animation rig, but its slab-sided Plane.001 hero body is replaced here by
# a higher-fidelity 2016 Tacoma DCLB body built from measured Tacoma proportions
# and the user's multi-angle truck-photo references.
# ---------------------------------------------------------------------------


def remove_obj(name):
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


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
        mod = o.modifiers.new('edge_soften', 'BEVEL')
        mod.width = bevel
        mod.segments = 2 if LOD == 0 else 1
        bpy.context.view_layer.objects.active = o
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception:
            pass
    return o


def loft(name, sections, mat, cap=True, bevel=0.0):
    verts = []
    n = len(sections[0][1])
    for x, ring in sections:
        if len(ring) != n:
            raise RuntimeError(f'{name}: inconsistent loft ring size')
        verts.extend([(x, y, z) for y, z in ring])
    faces = []
    for i in range(len(sections) - 1):
        a = i * n
        b = (i + 1) * n
        for j in range(n):
            k = (j + 1) % n
            faces.append((a + j, a + k, b + k, b + j))
    if cap:
        faces.append(tuple(range(n - 1, -1, -1)))
        off = (len(sections) - 1) * n
        faces.append(tuple(off + j for j in range(n)))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def prism_xz(name, profile, y_center, thickness, mat, bevel=0.0):
    y0 = y_center - thickness * 0.5
    y1 = y_center + thickness * 0.5
    verts = [(x, y0, z) for x, z in profile] + [(x, y1, z) for x, z in profile]
    n = len(profile)
    faces = [tuple(range(n - 1, -1, -1)), tuple(n + i for i in range(n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def prism_yz(name, profile, x_center, thickness, mat, bevel=0.0):
    x0 = x_center - thickness * 0.5
    x1 = x_center + thickness * 0.5
    verts = [(x0, y, z) for y, z in profile] + [(x1, y, z) for y, z in profile]
    n = len(profile)
    faces = [tuple(range(n - 1, -1, -1)), tuple(n + i for i in range(n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def panel3d(name, pts, mat, thickness=0.012):
    if len(pts) < 3:
        raise RuntimeError('panel requires >= 3 points')
    a, b, c = (Vector(pts[0]), Vector(pts[1]), Vector(pts[2]))
    n = (b - a).cross(c - a).normalized() * (thickness * 0.5)
    front = [tuple(Vector(p) + n) for p in pts]
    back = [tuple(Vector(p) - n) for p in pts]
    verts = front + back
    m = len(pts)
    faces = [tuple(range(m)), tuple(range(2*m - 1, m - 1, -1))]
    for i in range(m):
        j = (i + 1) % m
        faces.append((i, j, m + j, m + i))
    return mesh_obj(name, verts, faces, mat, True, 0.002 if LOD == 0 else 0.0)


def curve_tube(name, pts, radius, mat, resolution=2):
    c = bpy.data.curves.new(name + '_curve', 'CURVE')
    c.dimensions = '3D'
    c.bevel_depth = radius
    c.bevel_resolution = resolution if LOD == 0 else 1
    c.resolution_u = 1
    s = c.splines.new('POLY')
    s.points.add(len(pts) - 1)
    for p, co in zip(s.points, pts):
        p.co = (*co, 1.0)
    o = bpy.data.objects.new(name, c)
    bpy.context.collection.objects.link(o)
    c.materials.append(mat)
    return o


def arch_tube(name, cx, side, r, mat, zc=0.405, start=7.0, end=173.0):
    count = 22 if LOD == 0 else (14 if LOD == 1 else 8)
    pts = []
    for i in range(count):
        a = math.radians(start + (end - start) * i / (count - 1))
        pts.append((cx + r * math.cos(a), side * 0.958, zc + r * math.sin(a)))
    return curve_tube(name, pts, 0.042 if LOD == 0 else 0.035, mat, 2)


def ellipsoid(name, loc, scale, mat):
    seg = 28 if LOD == 0 else (18 if LOD == 1 else 12)
    rings = 16 if LOD == 0 else (10 if LOD == 1 else 8)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def ellipse_tube(name, x, cy, cz, ry, rz, radius, mat, tilt=0.0):
    count = 40 if LOD == 0 else 22
    pts = []
    ct, st = math.cos(tilt), math.sin(tilt)
    for i in range(count + 1):
        a = 2 * math.pi * i / count
        y0 = ry * math.cos(a)
        z0 = rz * math.sin(a)
        y = cy + y0 * ct - z0 * st
        z = cz + y0 * st + z0 * ct
        pts.append((x, y, z))
    return curve_tube(name, pts, radius, mat, 1)


def upper_arc_profile(cx, zc, r, x_front, x_rear, n=14):
    pts = []
    for i in range(n):
        x = x_front + (x_rear - x_front) * i / (n - 1)
        q = max(0.0, r*r - (x - cx)*(x - cx))
        z = zc + math.sqrt(q)
        pts.append((x, z))
    return pts


remove_obj('FBX_Plane.001')
for n in ('CAMPER_BODY', 'CAMPER_ROOF', 'CAMPER_SHELL'):
    remove_obj(n)
for pref in ('CAMPER_SIDE_GLASS_', 'CAMPER_REAR_GLASS', 'CAMPER_FRAME_', 'CAMPER_HATCH_'):
    remove_prefix(pref)

paint = M['burnt'] if DESTROYED else M['paint']
black = M['black']
metal = M['metal']
glass = M['glass']
lamp = M['lamp']
amber = M.get('aux_amber', M['amber'])

core_ring = [(-0.60,0.56),(-0.60,1.08),(-0.48,1.16),(0.48,1.16),(0.60,1.08),(0.60,0.56)]
loft('HERO_BODY_CORE', [(-2.98, core_ring), (2.58, core_ring)], paint, True, .025)

for side in (-1, 1):
    prism_xz(f'HERO_CAB_LOWER_{side}', [(-0.92,0.56),(-0.92,1.18),(0.78,1.18),(0.91,1.05),(0.84,0.56)], side*0.902, .075, paint, .025)

rear_arc = upper_arc_profile(-1.7855, .405, .585, -1.19, -2.38, 16 if LOD == 0 else 10)
for side in (-1, 1):
    prof = [(-3.03,.55),(-3.03,1.27),(-.86,1.27),(-.86,.58),(-1.12,.58)] + rear_arc + [(-2.48,.55)]
    prism_xz(f'HERO_BED_SIDE_{side}', prof, side*.905, .078, paint, .024)

front_arc = upper_arc_profile(1.7855, .405, .585, 2.38, 1.19, 16 if LOD == 0 else 10)
for side in (-1, 1):
    prof = [(.72,.57),(.72,1.16),(1.08,1.22),(1.62,1.27),(2.18,1.23),(2.63,1.10),(2.76,.87),(2.76,.57),(2.46,.57)] + front_arc + [(1.05,.57)]
    prism_xz(f'HERO_FRONT_FENDER_{side}', prof, side*.904, .082, paint, .025)

for side in (-1, 1):
    arch_tube(f'HERO_FLARE_FRONT_{side}', 1.7855, side, .607, black)
    arch_tube(f'HERO_FLARE_REAR_{side}', -1.7855, side, .607, black)


def hood_ring(width, zedge, zcrown, bottom):
    return [(-width,bottom),(-width,zedge),(-width*.62,(zedge+zcrown)*.5),(0,zcrown),(width*.62,(zedge+zcrown)*.5),(width,zedge),(width,bottom)]

loft('HERO_HOOD', [(.72, hood_ring(.79,1.145,1.185,1.095)),(1.18, hood_ring(.84,1.175,1.225,1.105)),(1.84, hood_ring(.86,1.175,1.235,1.095)),(2.36, hood_ring(.80,1.105,1.165,1.035))], paint, True, .020)

roof_ring = [(-.77,1.58),(-.74,1.72),(-.52,1.80),(0,1.835),(.52,1.80),(.74,1.72),(.77,1.58),(0,1.555)]
loft('HERO_CAB_ROOF', [(-.78, roof_ring), (.55, roof_ring)], paint, True, .018)
panel3d('HERO_WINDSHIELD', [(.82,-.82,1.18),(.82,.82,1.18),(.55,.72,1.70),(.55,-.72,1.70)], glass, .014)
panel3d('HERO_REAR_CAB_GLASS', [(-.84,.72,1.20),(-.84,-.72,1.20),(-.79,-.67,1.66),(-.79,.67,1.66)], glass, .014)

for side in (-1, 1):
    yb = side*.924; yt = side*.755
    panel3d(f'HERO_FRONT_WINDOW_{side}', [(.76,yb,1.20),(.06,yb,1.20),(.08,yt,1.67),(.55,yt,1.70)], glass, .012)
    panel3d(f'HERO_REAR_WINDOW_{side}', [(.02,yb,1.20),(-.72,yb,1.22),(-.70,yt,1.65),(.05,yt,1.67)], glass, .012)
    curve_tube(f'HERO_A_PILLAR_{side}', [(0.79,side*.925,1.18),(.54,side*.765,1.72)], .030, paint, 2)
    curve_tube(f'HERO_B_PILLAR_{side}', [(0.035,side*.927,1.18),(.065,side*.765,1.70)], .034, black, 1)
    curve_tube(f'HERO_C_PILLAR_{side}', [(-.76,side*.925,1.18),(-.71,side*.765,1.69)], .036, paint, 2)
    curve_tube(f'HERO_WINDOW_SILL_{side}', [(-.77,side*.932,1.185),(.79,side*.932,1.185)], .018, black, 1)

for side in (-1, 1):
    y = side*.946
    for x in (-.05, .77, -.82):
        curve_tube(f'HERO_DOOR_SEAM_{side}_{x}', [(x,y,.64),(x,y,1.18)], .007, black, 0)
    curve_tube(f'HERO_BODY_CREASE_{side}', [(-.82,y,.92),(-.15,y,.90),(.55,y,.94),(.80,y,.99)], .008, black, 0)
    for x in (.38,-.48):
        curve_tube(f'HERO_HANDLE_{side}_{x}', [(x-.07,y+.004*side,1.105),(x+.07,y+.004*side,1.105)], .014, black, 1)

for side in (-1,1):
    ellipsoid(f'HERO_MIRROR_CAP_{side}', (.69, side*1.045, 1.42), (.15,.095,.075), paint)
    ellipsoid(f'HERO_MIRROR_LOWER_{side}', (.66, side*.994, 1.385), (.10,.060,.045), black)
    curve_tube(f'HERO_MIRROR_STEM_{side}', [(.61,side*.94,1.34),(.66,side*1.00,1.39)], .024, black, 1)

prism_yz('HERO_TAILGATE', [(-.86,.61),(-.86,1.22),(.86,1.22),(.86,.61)], -3.045, .055, paint, .020)
for side in (-1,1):
    curve_tube(f'HERO_BED_RAIL_{side}', [(-3.00,side*.925,1.275),(-.88,side*.925,1.275)], .022, black, 1)


def topper_ring(hw, zbottom, zside, zshoulder, zcrown):
    return [(-hw,zbottom),(-hw,zside),(-hw*.78,zshoulder),(0,zcrown),(hw*.78,zshoulder),(hw,zside),(hw,zbottom),(0,zbottom-.02)]

loft('HERO_CAMPER_SHELL', [(-2.91, topper_ring(.80,1.17,1.51,1.68,1.74)),(-2.76, topper_ring(.86,1.17,1.58,1.75,1.81)),(-1.05, topper_ring(.86,1.17,1.60,1.77,1.82)),(-.88, topper_ring(.79,1.17,1.54,1.70,1.77))], paint, True, .025)

for side in (-1,1):
    y = side*.866
    panel3d(f'HERO_CAMPER_SIDE_GLASS_{side}', [(-2.55,y,1.28),(-1.17,y,1.28),(-1.11,side*.82,1.68),(-2.48,side*.82,1.68)], glass, .010)
    curve_tube(f'HERO_CAMPER_TOP_FRAME_{side}', [(-2.52,y,1.70),(-1.12,y,1.70)], .018, black, 1)
    curve_tube(f'HERO_CAMPER_BOTTOM_FRAME_{side}', [(-2.58,y,1.26),(-1.15,y,1.26)], .018, black, 1)
    curve_tube(f'HERO_CAMPER_FRONT_FRAME_{side}', [(-1.13,y,1.26),(-1.10,side*.82,1.69)], .018, black, 1)
    curve_tube(f'HERO_CAMPER_REAR_FRAME_{side}', [(-2.58,y,1.26),(-2.49,side*.82,1.69)], .018, black, 1)
    curve_tube(f'HERO_CAMPER_DIVIDER_{side}', [(-1.86,y,1.27),(-1.84,side*.83,1.69)], .015, black, 1)

panel3d('HERO_CAMPER_REAR_GLASS', [(-2.925,-.69,1.26),(-2.925,.69,1.26),(-2.885,.63,1.68),(-2.885,-.63,1.68)], glass, .012)
curve_tube('HERO_CAMPER_HATCH_HANDLE', [(-2.958,-.10,1.205),(-2.958,.10,1.205)], .018, black, 1)

outer_grille = [(-.66,.70),(-.79,.86),(-.70,1.15),(-.50,1.25),(.50,1.25),(.70,1.15),(.79,.86),(.66,.70)]
prism_yz('HERO_GRILLE_SURROUND', outer_grille, 2.69, .065, black, .020)
inner_grille = [(-.57,.76),(-.67,.88),(-.60,1.10),(-.44,1.17),(.44,1.17),(.60,1.10),(.67,.88),(.57,.76)]
prism_yz('HERO_GRILLE_INNER', inner_grille, 2.732, .025, black, .010)

if LOD < 2:
    for z in (.82,.91,1.00,1.09):
        curve_tube(f'HERO_GRILLE_BAR_{z}', [(2.755,-.58,z),(2.755,.58,z)], .012 if LOD == 0 else .016, metal, 1)
    if LOD == 0:
        for y in (-.50,-.34,-.17,0,.17,.34,.50):
            curve_tube(f'HERO_GRILLE_VERT_{y}', [(2.757,y,.78),(2.757,y,1.13)], .006, metal, 0)

ellipse_tube('HERO_TOYOTA_OUTER', 2.785, 0, .965, .135, .085, .014, black)
ellipse_tube('HERO_TOYOTA_INNER_V', 2.789, 0, .968, .055, .072, .010, black)
ellipse_tube('HERO_TOYOTA_INNER_H', 2.792, 0, .968, .095, .030, .009, black)

for side in (-1,1):
    y0 = side*.69; y1 = side*.93
    if side > 0:
        hp = [(y0,.99),(y1,.94),(y1,1.14),(y0,1.19)]
        ap = [(side*.885,.96),(side*.955,.95),(side*.955,1.12),(side*.885,1.13)]
    else:
        hp = [(y1,.94),(y0,.99),(y0,1.19),(y1,1.14)]
        ap = [(side*.955,.95),(side*.885,.96),(side*.885,1.13),(side*.955,1.12)]
    prism_yz(f'HERO_HEADLAMP_{side}', hp, 2.706, .050, lamp, .012)
    prism_yz(f'HERO_AMBER_MARKER_{side}', ap, 2.711, .052, amber, .008)
    prism_yz(f'HERO_FRONT_BUMPER_WING_{side}', [(side*.70,.56),(side*.93,.60),(side*.94,.86),(side*.77,.90)], 2.70, .10, paint, .025)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24 if LOD == 0 else 14, radius=.085, depth=.035, location=(2.765,side*.70,.64), rotation=(0,math.pi/2,0))
    fog = bpy.context.object; fog.name=f'HERO_FOG_{side}'; fog.data.materials.append(lamp)
    ellipse_tube(f'HERO_FOG_BEZEL_{side}', 2.785, side*.70, .64, .105, .105, .012, black)

prism_yz('HERO_LOWER_VALANCE', [(-.70,.48),(-.92,.57),(-.86,.72),(.86,.72),(.92,.57),(.70,.48)], 2.66, .12, paint, .025)

for o in bpy.data.objects:
    if o.name.startswith('FRONT_LED_BAR_') or o.name.startswith('FRONT_LED_CELL_'):
        o.location.x -= .035

if DESTROYED:
    for o in bpy.data.objects:
        if o.name.startswith('HERO_') and o.type == 'MESH' and o.data.materials:
            if o.data.materials[0] == M['paint']:
                o.data.materials[0] = M['burnt']

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch6 complete: higher-fidelity 2016 Tacoma hero body/topper/front fascia rebuild; validated wheel rig preserved')
