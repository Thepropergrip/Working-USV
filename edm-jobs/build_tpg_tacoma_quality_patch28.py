import runpy
import math
import bpy

# Geometry-only consolidation pass layered on export/package-green patch27.
# The four-view clay QA showed that many historical front-clip overlays were
# individually small but accumulated into a rectangular/armored-looking nose.
# Patch28 removes only those visible front overlays and rebuilds the 2016 Tacoma
# fascia as one coherent system: painted hex surround, recessed black grille,
# slim swept lamps, body-colour bumper corners, compact fog pockets and a slim
# integrated lower LED bar. DCS mechanics, wheel animation, collision, tuning,
# LOD/destroyed structure, official ED exporter and Mods/tech packaging stay intact.
ns27 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch27.py', run_name='__main__')
LOD = ns27['LOD']
mesh_obj = ns27['mesh_obj']
curve_tube = ns27['curve_tube']
remove = ns27['remove']


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)


def prism_yz(name, profile, x0, x1, mat, bevel=0.0):
    verts = [(x0, y, z) for y, z in profile] + [(x1, y, z) for y, z in profile]
    n = len(profile)
    faces = [tuple(range(n - 1, -1, -1)), tuple(n + i for i in range(n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def ring_prism_yz(name, outer, inner, x0, x1, mat, bevel=0.0):
    # Outer/inner must have the same point count and matching winding.
    n = len(outer)
    if n != len(inner):
        raise RuntimeError('ring profile size mismatch')
    verts = ([(x0, y, z) for y, z in outer] +
             [(x1, y, z) for y, z in outer] +
             [(x0, y, z) for y, z in inner] +
             [(x1, y, z) for y, z in inner])
    faces = []
    for i in range(n):
        j = (i + 1) % n
        # front and rear annulus strips
        faces.append((n+i, n+j, 3*n+j, 3*n+i))
        faces.append((i, 2*n+i, 2*n+j, j))
        # outer and inner depth walls
        faces.append((i, j, n+j, n+i))
        faces.append((2*n+i, 3*n+i, 3*n+j, 2*n+j))
    return mesh_obj(name, verts, faces, mat, True, bevel)


def ellipse_tube(name, x, cy, cz, ry, rz, radius, mat, count=30):
    pts = []
    for i in range(count + 1):
        a = math.tau * i / count
        pts.append((x, cy + ry * math.cos(a), cz + rz * math.sin(a)))
    return curve_tube(name, pts, radius, mat, 1)


# Cache materials before retiring the prior front system.
paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]
lamp_obj = bpy.data.objects.get('HERO_HEADLAMP_1') or bpy.data.objects.get('HERO_FOG_1')
lamp = lamp_obj.data.materials[0] if lamp_obj and lamp_obj.data.materials else black
amber_obj = bpy.data.objects.get('HERO_AMBER_MARKER_1')
amber = amber_obj.data.materials[0] if amber_obj and amber_obj.data.materials else lamp
metal_obj = bpy.data.objects.get('HERO_GRILLE_SLAT_0')
metal = metal_obj.data.materials[0] if metal_obj and metal_obj.data.materials else black
aux_obj = bpy.data.objects.get('FRONT_LED_BAR_LENS')
aux_led = aux_obj.data.materials[0] if aux_obj and aux_obj.data.materials else lamp

# Retire the accumulated fascia/lamp/bumper overlays as one system. Keep the
# validated hero hood/cab/topper and wheel rig untouched.
for pref in (
    'HERO_GRILLE_', 'HERO_TOYOTA_P13_', 'HERO_HEADLAMP_',
    'HERO_AMBER_MARKER_', 'HERO_FRONT_BUMPER_', 'HERO_FOG_',
    'HERO_P23_', 'HERO_P24_', 'HERO_P25_', 'HERO_P27_'
):
    remove_prefix(pref)
for name in ('HERO_P20_NOSE_BACKING', 'HERO_P20_CLAMP_CHIN', 'HERO_HOOD_LEADING_SEAM'):
    remove(name)
for side in (-1, 1):
    remove(f'HERO_P20_CLAMP_WING_{side}')

# The old lower-grille LED implementation read as a row of teeth in clay QA.
for pref in ('FRONT_LED_BAR_', 'FRONT_LED_CELL_'):
    remove_prefix(pref)

# Painted upper fascia bridges the muscular hood into the lamps/grille without
# the black triangular gaps visible in patch27 front-3Q.
panel('HERO_P28_UPPER_FASCIA', [
    (2.40,-.47,1.220), (2.50,-.59,1.190), (2.61,-.54,1.155),
    (2.675,-.42,1.145), (2.675,.42,1.145), (2.61,.54,1.155),
    (2.50,.59,1.190), (2.40,.47,1.220)
], paint)

# Stock-like hex surround with an actual open center so the black grille is
# visibly recessed instead of another flat rectangular plate.
outer = [(-.690,1.155),(-.770,1.070),(-.735,.820),(-.600,.745),
         (.600,.745),(.735,.820),(.770,1.070),(.690,1.155)]
inner = [(-.585,1.105),(-.645,1.035),(-.615,.850),(-.515,.790),
         (.515,.790),(.615,.850),(.645,1.035),(.585,1.105)]
ring_prism_yz('HERO_P28_GRILLE_SURROUND', outer, inner, 2.655, 2.705, paint, .008)
prism_yz('HERO_P28_GRILLE_RECESS', inner, 2.645, 2.682, black, .004)

# Two restrained grille bars and a compact center oval provide recognition
# without dominating the entire nose in clay.
if LOD < 2:
    for i, z in enumerate((.895, 1.005)):
        curve_tube(f'HERO_P28_GRILLE_BAR_{i}', [(2.690,-.545,z),(2.690,.545,z)], .0048, metal, 1)
    ellipse_tube('HERO_P28_TOYOTA_OUTER', 2.699, 0, .950, .090, .055, .0065, metal, 28 if LOD == 0 else 18)
    ellipse_tube('HERO_P28_TOYOTA_INNER', 2.701, 0, .950, .044, .041, .0045, metal, 24 if LOD == 0 else 16)
    curve_tube('HERO_P28_TOYOTA_BAR', [(2.702,-.060,.950),(2.702,.060,.950)], .0045, metal, 1)

# Slim swept high-mounted headlamps. Black recesses sit behind the lenses and
# taper into the fender, matching the 2016 truck's horizontal eye shape.
for side in (-1, 1):
    s = side
    housing = [(s*.555,1.120),(s*.655,1.135),(s*.825,1.115),(s*.925,1.070),
               (s*.945,1.015),(s*.875,.985),(s*.650,.995),(s*.565,1.035)]
    lensprof = [(s*.575,1.105),(s*.660,1.118),(s*.810,1.100),(s*.900,1.062),
                (s*.915,1.025),(s*.855,1.002),(s*.665,1.010),(s*.590,1.045)]
    prism_yz(f'HERO_P28_LAMP_RECESS_{side}', housing, 2.675, 2.700, black, .004)
    prism_yz(f'HERO_P28_HEADLAMP_{side}', lensprof, 2.700, 2.712, lamp, .003)
    # small amber outer tip
    amberprof = [(s*.900,1.064),(s*.932,1.047),(s*.940,1.020),(s*.904,1.006),(s*.875,1.020)]
    prism_yz(f'HERO_P28_AMBER_{side}', amberprof, 2.712, 2.718, amber, .002)

    if LOD < 2:
        for idx, (yy, zz, rr) in enumerate(((.700,1.063,.032),(.790,1.055,.024))):
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=22 if LOD == 0 else 14,
                radius=rr, depth=.008,
                location=(2.718, s*yy, zz),
                rotation=(0, math.pi/2, 0)
            )
            p = bpy.context.object
            p.name = f'HERO_P28_PROJECTOR_{side}_{idx}'
            p.data.materials.append(lamp)

# Body-colour bumper corners sweep under the lamps while leaving the center
# lower opening black, avoiding patch27's armored vertical towers.
for side in (-1, 1):
    s = side
    prism_yz(f'HERO_P28_BUMPER_CORNER_{side}', [
        (s*.935,.585),(s*.955,.685),(s*.925,.805),(s*.855,.900),
        (s*.735,.915),(s*.650,.825),(s*.665,.705),(s*.790,.605)
    ], 2.625, 2.685, paint, .010)

    # Compact stock-position fog pocket integrated into the corner.
    pocket = [(s*.755,.595),(s*.825,.605),(s*.855,.650),(s*.825,.720),
              (s*.755,.730),(s*.715,.680),(s*.715,.625)]
    prism_yz(f'HERO_P28_FOG_POCKET_{side}', pocket, 2.680, 2.700, black, .004)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24 if LOD == 0 else 14,
        radius=.042, depth=.010,
        location=(2.707, s*.780, .658),
        rotation=(0, math.pi/2, 0)
    )
    fog = bpy.context.object
    fog.name = f'HERO_P28_FOG_{side}'
    fog.data.materials.append(lamp)

# Clean black lower opening and a shallow painted lip. This is deliberately
# simple because silhouette comes before accessory detail.
prism_yz('HERO_P28_LOWER_OPENING', [
    (-.600,.715),(-.690,.665),(-.655,.545),(.655,.545),(.690,.665),(.600,.715)
], 2.655, 2.695, black, .006)
prism_yz('HERO_P28_LOWER_LIP', [
    (-.670,.535),(-.720,.505),(-.650,.475),(.650,.475),(.720,.505),(.670,.535)
], 2.630, 2.675, paint, .006)

# Recreate the user's slim lower-grille LED bar as a flush integrated element,
# not a protruding segmented row.
prism_yz('HERO_P28_LED_BODY', [(-.405,.635),(-.405,.592),(.405,.592),(.405,.635)],
         2.695, 2.710, black, .003)
if LOD == 0:
    prism_yz('HERO_P28_LED_LENS', [(-.355,.624),(-.355,.604),(.355,.604),(.355,.624)],
             2.710, 2.716, aux_led, .002)

# Restrained hood leading break, now following the actual hex surround width.
if LOD < 2:
    curve_tube('HERO_P28_HOOD_NOSE_SEAM', [
        (2.38,-.50,1.218),(2.49,-.57,1.190),(2.61,-.50,1.160),
        (2.665,-.39,1.148),(2.665,.39,1.148),(2.61,.50,1.160),
        (2.49,.57,1.190),(2.38,.50,1.218)
    ], .0045, black, 1)

# Exporter UV safety for all newly created mesh objects.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons or len(obj.data.uv_layers):
        continue
    me = obj.data
    uv = me.uv_layers.new(name='UVMap')
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    dx = max(xmax-xmin, 1e-6)
    dy = max(ymax-ymin, 1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co.x-xmin)/dx, (co.y-ymin)/dy)
    me.uv_layers.active = uv

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch28 complete: consolidated stock-like 2016 front fascia, recessed hex grille, swept lamps, integrated bumper/fogs and slim LED bar; DCS mechanics untouched')
