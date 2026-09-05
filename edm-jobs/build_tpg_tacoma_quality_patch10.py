import runpy
import math
import bpy

# Geometry-only front-clip recognition pass layered on patch9.
# Preserve the proven wheel rig, DCS registration/tuning, LOD/destroyed structure,
# exporter pipeline and package layout.  This patch specifically fixes the
# visually rejected flat-wall front face by replacing the solid grille plates
# with an open, sculpted Tacoma-like fascia.
ns = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch9.py', run_name='__main__')
LOD = ns['LOD']
mesh_obj = ns['mesh_obj']
curve_tube = ns['curve_tube']
remove = ns['remove']


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


# Cache materials from the proven patch9 objects before replacing the fascia.
paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_GRILLE_SURROUND'].data.materials[0]
lamp = bpy.data.objects['HERO_HEADLAMP_1'].data.materials[0]
amber = bpy.data.objects['HERO_AMBER_MARKER_1'].data.materials[0]
metal = bpy.data.objects['HERO_GRILLE_BAR_0.82'].data.materials[0] if bpy.data.objects.get('HERO_GRILLE_BAR_0.82') else black

# Remove the old solid plate-style fascia.  Those filled polygons read as a
# featureless rectangular wall in the QA front and front-3Q renders.
for name in ('HERO_GRILLE_SURROUND', 'HERO_GRILLE_INNER', 'HERO_LOWER_VALANCE'):
    remove(name)
for obj in list(bpy.data.objects):
    if obj.name.startswith('HERO_GRILLE_BAR_') or obj.name.startswith('HERO_GRILLE_VERT_') \
       or obj.name.startswith('HERO_TOYOTA_') or obj.name.startswith('HERO_HEADLAMP_') \
       or obj.name.startswith('HERO_AMBER_MARKER_') or obj.name.startswith('HERO_FRONT_BUMPER_WING_') \
       or obj.name.startswith('HERO_FOG_'):
        bpy.data.objects.remove(obj, do_unlink=True)

# Open hex/trapezoid grille outline, narrower at the lower corners and visibly
# separated from the bumper.  The open center is intentional: it keeps the nose
# from reverting to the slab/wall silhouette seen in patch9 QA.
outer = [
    (2.742, -0.57, 1.135),
    (2.742, -0.69, 1.055),
    (2.742, -0.72, 0.865),
    (2.742, -0.57, 0.735),
    (2.742,  0.57, 0.735),
    (2.742,  0.72, 0.865),
    (2.742,  0.69, 1.055),
    (2.742,  0.57, 1.135),
    (2.742, -0.57, 1.135),
]
curve_tube('HERO_GRILLE_FRAME', outer, .025 if LOD == 0 else .032, black, 2)

# Recessed grille slats provide depth without closing the opening.
if LOD < 2:
    for i, z in enumerate((.80, .875, .95, 1.025, 1.095)):
        half = .58 - abs(z - .94) * .30
        curve_tube(f'HERO_GRILLE_SLAT_{i}', [(2.715, -half, z), (2.715, half, z)], .010 if LOD == 0 else .014, metal, 1)
    if LOD == 0:
        for i, y in enumerate((-.42, -.21, 0.0, .21, .42)):
            curve_tube(f'HERO_GRILLE_MESH_{i}', [(2.710, y, .79), (2.710, y, 1.105)], .005, black, 0)

# 2016 Tacoma-like swept headlamp pockets: broad at the grille, tapering toward
# the fenders, with separate amber outer corners.  Keep them thin and slightly
# proud of the fascia so the shapes survive clay QA.
left_head = [(-.91,.985),(-.70,1.145),(-.55,1.135),(-.60,.955),(-.83,.915)]
right_head = [( .91,.985),( .70,1.145),( .55,1.135),( .60,.955),( .83,.915)]
prism_yz('HERO_HEADLAMP_-1', left_head, 2.735, .050, lamp, .012)
prism_yz('HERO_HEADLAMP_1', right_head, 2.735, .050, lamp, .012)
prism_yz('HERO_AMBER_MARKER_-1', [(-.95,.935),(-.89,1.035),(-.82,1.015),(-.84,.915)], 2.755, .030, amber, .006)
prism_yz('HERO_AMBER_MARKER_1', [( .95,.935),( .89,1.035),( .82,1.015),( .84,.915)], 2.755, .030, amber, .006)

# Painted bumper shoulders are now chamfered instead of tall rectangular wings.
prism_yz('HERO_FRONT_BUMPER_WING_-1', [(-.94,.57),(-.91,.83),(-.77,.90),(-.66,.78),(-.68,.58)], 2.695, .105, paint, .020)
prism_yz('HERO_FRONT_BUMPER_WING_1', [( .94,.57),( .91,.83),( .77,.90),( .66,.78),( .68,.58)], 2.695, .105, paint, .020)

# Lower center valance follows the grille taper and leaves a break between the
# main grille and bumper, a key front-3Q cue missing in the rejected render.
prism_yz('HERO_LOWER_VALANCE', [(-.67,.49),(-.88,.58),(-.82,.70),(-.58,.745),(.58,.745),(.82,.70),(.88,.58),(.67,.49)], 2.675, .105, black, .018)

# Compact fog lamps and bezels, inset below the headlights.
for side in (-1, 1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24 if LOD == 0 else 14,
                                       radius=.070, depth=.028,
                                       location=(2.742, side*.70, .635),
                                       rotation=(0, math.pi/2, 0))
    fog = bpy.context.object
    fog.name = f'HERO_FOG_{side}'
    fog.data.materials.append(lamp)
    curve_tube(f'HERO_FOG_BEZEL_{side}', [
        (2.758, side*(.70-.085), .635),
        (2.758, side*(.70-.060), .695),
        (2.758, side*(.70+.060), .695),
        (2.758, side*(.70+.085), .635),
        (2.758, side*(.70+.060), .575),
        (2.758, side*(.70-.060), .575),
        (2.758, side*(.70-.085), .635),
    ], .010, black, 1)

# Add a shallow center hood power bulge and two edge creases to break up the
# broad flat hood plane in front-3Q without altering its validated footprint.
curve_tube('HERO_HOOD_CENTER_CUE', [(1.00,0,1.185),(1.55,0,1.215),(2.18,0,1.175)], .010, paint, 1)
for side in (-1,1):
    curve_tube(f'HERO_HOOD_CREASE_{side}', [(1.03,side*.47,1.158),(1.62,side*.55,1.190),(2.22,side*.50,1.145)], .008, paint, 1)

# Guarantee UVs for all replacement meshes for the ED material exporter.
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
print('[TPG TACOMA] quality patch10 complete: open sculpted Tacoma front fascia, swept lamps, chamfered bumper and hood cues; DCS mechanics untouched')
