import runpy
import math
import bpy

# Geometry-only recognition/silhouette pass layered on patch11.
# Visual target: the user's 2016 Tacoma TRD Off Road 4x4 DCLB with paint-matched
# A.R.E.-style long-bed shell and low-profile cab platform.  DCS registration,
# speed tuning, arg-8 wheel roll, arg-9 steering, collision, LOD/destroyed
# structure, official ED exporter and package layout are intentionally untouched.
ns11 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch11.py', run_name='__main__')
LOD = ns11['LOD']
loft = ns11['loft']
panel = ns11['panel']
curve_tube = ns11['curve_tube']
remove = ns11['remove']
mesh_obj = ns11['base']['mesh_obj']


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


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


def box(name, loc, dims, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
    if bevel > 0 and LOD < 2:
        m = o.modifiers.new('edge_soften', 'BEVEL')
        m.width = bevel
        m.segments = 2 if LOD == 0 else 1
        bpy.context.view_layer.objects.active = o
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception:
            pass
    return o


# Cache materials before replacing geometry.
paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
glass = bpy.data.objects['HERO_WINDSHIELD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]
lamp = bpy.data.objects['HERO_HEADLAMP_1'].data.materials[0]
amber = bpy.data.objects['HERO_AMBER_MARKER_1'].data.materials[0]
metal_obj = bpy.data.objects.get('HERO_GRILLE_SLAT_0')
metal = metal_obj.data.materials[0] if metal_obj and metal_obj.data.materials else black
rack_obj = bpy.data.objects.get('CAB_RACK_FRONT_RAIL') or bpy.data.objects.get('RACK_RAIL_0_1')
rack_mat = rack_obj.data.materials[0] if rack_obj and rack_obj.data.materials else metal

# ---------------------------------------------------------------------------
# CAB / GREENHOUSE
# Patch11 proved the general wheelbase and body stations, but its side glazing
# still formed a wedge.  Rebuild the visible upper cab with larger, squarer
# double-cab windows, thinner pillars, a shallow stock roof crown and realistic
# separation from the camper shell.
# ---------------------------------------------------------------------------
for n in ('HERO_CAB_ROOF', 'HERO_WINDSHIELD', 'HERO_REAR_CAB_GLASS'):
    remove(n)
for side in (-1, 1):
    for stem in ('HERO_FRONT_WINDOW_', 'HERO_REAR_WINDOW_', 'HERO_A_PILLAR_',
                 'HERO_B_PILLAR_', 'HERO_C_PILLAR_', 'HERO_WINDOW_SILL_',
                 'HERO_ROOF_DRIP_'):
        remove(stem + str(side))


def roof_ring(hw, zbase, zedge, shoulder, crown):
    return [(-hw, zbase), (-hw, zedge), (-hw*.72, shoulder), (-hw*.34, crown-.010),
            (0, crown), (hw*.34, crown-.010), (hw*.72, shoulder), (hw, zedge), (hw, zbase)]

loft('HERO_CAB_ROOF', [
    (-.94, roof_ring(.655, 1.610, 1.670, 1.750, 1.792)),
    (-.80, roof_ring(.705, 1.615, 1.700, 1.775, 1.812)),
    (-.18, roof_ring(.730, 1.620, 1.710, 1.785, 1.822)),
    (.32,  roof_ring(.710, 1.605, 1.695, 1.765, 1.802)),
    (.56,  roof_ring(.645, 1.565, 1.640, 1.715, 1.760)),
], paint, .010)

# Windshield remains distinctly raked, but its top is wider and its brow less
# pinched.  The rear window is close to upright as on the double cab.
panel('HERO_WINDSHIELD', [(.875,-.825,1.145),(.875,.825,1.145),(.535,.665,1.695),(.535,-.665,1.695)], glass, .010)
panel('HERO_REAR_CAB_GLASS', [(-.945,.665,1.205),(-.945,-.665,1.205),(-.915,-.625,1.665),(-.915,.625,1.665)], glass, .010)

for side in (-1, 1):
    yb = side*.928
    yt = side*.735
    # Front door glass: broad Tacoma rectangle with only the A-pillar edge raked.
    panel(f'HERO_FRONT_WINDOW_{side}', [
        (.815,yb,1.185),(.015,yb,1.185),(.020,yt,1.665),(.515,side*.670,1.695)
    ], glass, .009)
    # Rear door glass: near-rectangular with a mild C-pillar kick, not a wedge.
    panel(f'HERO_REAR_WINDOW_{side}', [
        (-.015,yb,1.185),(-.805,yb,1.205),(-.855,side*.700,1.650),(-.015,yt,1.665)
    ], glass, .009)
    curve_tube(f'HERO_A_PILLAR_{side}', [(.845,side*.930,1.155),(.525,side*.680,1.708)], .021, paint, 2)
    curve_tube(f'HERO_B_PILLAR_{side}', [(.000,side*.932,1.180),(.005,side*.740,1.682)], .024, black, 1)
    curve_tube(f'HERO_C_PILLAR_{side}', [(-.820,side*.930,1.190),(-.875,side*.705,1.670)], .024, paint, 2)
    curve_tube(f'HERO_WINDOW_SILL_{side}', [(-.825,side*.936,1.188),(.825,side*.936,1.178)], .013, black, 1)
    curve_tube(f'HERO_ROOF_DRIP_{side}', [(-.875,side*.690,1.692),(-.30,side*.725,1.760),(.30,side*.705,1.742),(.515,side*.655,1.700)], .007, black, 1)

# ---------------------------------------------------------------------------
# PAINT-MATCHED LONG-BED CAMPER SHELL
# The reference truck's shell roof nearly follows the cab height. Patch11's
# low wedge made the bed look chopped. Raise it, flatten the longitudinal crown,
# enlarge the side glass and keep only mild front/rear taper.
# ---------------------------------------------------------------------------
for n in ('HERO_CAMPER_SHELL', 'HERO_CAMPER_REAR_GLASS'):
    remove(n)
for side in (-1, 1):
    for stem in ('HERO_CAMPER_SIDE_GLASS_', 'HERO_CAMPER_TOP_FRAME_',
                 'HERO_CAMPER_BOTTOM_FRAME_', 'HERO_CAMPER_FRONT_FRAME_',
                 'HERO_CAMPER_REAR_FRAME_', 'HERO_CAMPER_DIVIDER_'):
        remove(stem + str(side))


def cap_ring(hw, zbottom, zside, shoulder, crown):
    return [(-hw,zbottom),(-hw,zside),(-hw*.74,shoulder),(-hw*.34,crown-.010),
            (0,crown),(hw*.34,crown-.010),(hw*.74,shoulder),(hw,zside),(hw,zbottom)]

loft('HERO_CAMPER_SHELL', [
    (-3.00, cap_ring(.755,1.180,1.525,1.675,1.735)),
    (-2.88, cap_ring(.815,1.180,1.585,1.725,1.775)),
    (-1.22, cap_ring(.820,1.180,1.595,1.735,1.785)),
    (-1.06, cap_ring(.770,1.180,1.550,1.690,1.755)),
], paint, .012)

for side in (-1, 1):
    y = side*.825
    panel(f'HERO_CAMPER_SIDE_GLASS_{side}', [
        (-2.76,y,1.285),(-1.25,y,1.285),(-1.15,side*.785,1.690),(-2.70,side*.790,1.690)
    ], glass, .009)
    curve_tube(f'HERO_CAMPER_TOP_FRAME_{side}', [(-2.70,y,1.705),(-1.15,y,1.705)], .013, black, 1)
    curve_tube(f'HERO_CAMPER_BOTTOM_FRAME_{side}', [(-2.76,y,1.272),(-1.25,y,1.272)], .013, black, 1)
    curve_tube(f'HERO_CAMPER_FRONT_FRAME_{side}', [(-1.25,y,1.275),(-1.15,side*.790,1.705)], .014, black, 1)
    curve_tube(f'HERO_CAMPER_REAR_FRAME_{side}', [(-2.76,y,1.275),(-2.70,side*.790,1.705)], .014, black, 1)
    curve_tube(f'HERO_CAMPER_DIVIDER_{side}', [(-1.94,y,1.278),(-1.93,side*.800,1.705)], .012, black, 1)

panel('HERO_CAMPER_REAR_GLASS', [(-3.012,-.655,1.270),(-3.012,.655,1.270),(-2.970,.595,1.690),(-2.970,-.595,1.690)], glass, .010)

# ---------------------------------------------------------------------------
# 2016 TACOMA FRONT COMPOSITION
# Replace the patch10 tube/cage-looking fascia with a stock-like recessed grille,
# broader horizontal lamps, body-colour corner shoulders and compact black lower
# valance. This is deliberately geometry-first: clay must read "Tacoma" before
# grille texture or lamp internals are polished.
# ---------------------------------------------------------------------------
for n in ('HERO_GRILLE_FACE', 'HERO_LOWER_VALANCE'):
    remove(n)
for pref in ('HERO_GRILLE_', 'HERO_HEADLAMP_', 'HERO_AMBER_MARKER_',
             'HERO_FRONT_BUMPER_WING_', 'HERO_FOG_'):
    remove_prefix(pref)

# Recessed stock-proportion grille face: broad but not the oversized armored mask.
grille = [(-.590,.770),(-.690,.855),(-.655,1.080),(-.535,1.155),
          (.535,1.155),(.655,1.080),(.690,.855),(.590,.770)]
prism_yz('HERO_GRILLE_FACE', grille, 2.720, .040, black, .014)

if LOD < 2:
    for i, z in enumerate((.820,.895,.970,1.045,1.105)):
        half = .565 if z < 1.05 else .525
        curve_tube(f'HERO_GRILLE_SLAT_{i}', [(2.745,-half,z),(2.745,half,z)], .009 if LOD == 0 else .012, metal, 1)
    if LOD == 0:
        # restrained vertical mesh rhythm, recessed behind the bars
        for i, y in enumerate((-.43,-.215,0,.215,.43)):
            curve_tube(f'HERO_GRILLE_MESH_{i}', [(2.738,y,.815),(2.738,y,1.115)], .0045, black, 0)

# Broad third-gen headlamps carry far into the fenders and remain visibly larger
# than the amber outer corner, matching the reference truck's front identity.
left_lamp = [(-.955,.955),(-.900,1.105),(-.785,1.175),(-.555,1.155),(-.590,.955),(-.790,.915)]
right_lamp = [( .955,.955),( .900,1.105),( .785,1.175),( .555,1.155),( .590,.955),( .790,.915)]
prism_yz('HERO_HEADLAMP_-1', left_lamp, 2.735, .052, lamp, .010)
prism_yz('HERO_HEADLAMP_1', right_lamp, 2.735, .052, lamp, .010)
prism_yz('HERO_AMBER_MARKER_-1', [(-.960,.955),(-.910,1.075),(-.850,1.095),(-.835,.930)], 2.758, .028, amber, .005)
prism_yz('HERO_AMBER_MARKER_1', [( .960,.955),( .910,1.075),( .850,1.095),( .835,.930)], 2.758, .028, amber, .005)

# Sculpted body-colour bumper corners; less vertical mass than patch10.
prism_yz('HERO_FRONT_BUMPER_WING_-1', [(-.945,.575),(-.930,.800),(-.800,.900),(-.690,.850),(-.650,.690),(-.690,.575)], 2.685, .100, paint, .018)
prism_yz('HERO_FRONT_BUMPER_WING_1', [( .945,.575),( .930,.800),( .800,.900),( .690,.850),( .650,.690),( .690,.575)], 2.685, .100, paint, .018)
prism_yz('HERO_LOWER_VALANCE', [(-.665,.500),(-.820,.570),(-.760,.700),(-.560,.745),(.560,.745),(.760,.700),(.820,.570),(.665,.500)], 2.670, .095, black, .014)

for side in (-1, 1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24 if LOD == 0 else 14,
                                       radius=.066, depth=.024,
                                       location=(2.733, side*.720, .650),
                                       rotation=(0, math.pi/2, 0))
    fog = bpy.context.object
    fog.name = f'HERO_FOG_{side}'
    fog.data.materials.append(lamp)
    curve_tube(f'HERO_FOG_BEZEL_{side}', [
        (2.750,side*.650,.650),(2.750,side*.670,.705),(2.750,side*.750,.705),
        (2.750,side*.790,.650),(2.750,side*.750,.595),(2.750,side*.670,.595),
        (2.750,side*.650,.650)
    ], .008, black, 1)

# ---------------------------------------------------------------------------
# SILHOUETTE CONTAMINATION: LOW-PROFILE CAB PLATFORM
# The previous duplicated rack members visually doubled the roof thickness.
# Remove both generations and rebuild one restrained cab-only platform. This is
# a silhouette correction, not accessory-detail polish.
# ---------------------------------------------------------------------------
for pref in ('RACK_RAIL_0_', 'RACK_FOOT_0_', 'RACK_BAR_0_', 'CAB_RACK_'):
    remove_prefix(pref)

rail_z = 1.866
for side in (-1, 1):
    box(f'HERO_CAB_RACK_SIDE_{side}', (.08,side*.665,rail_z), (1.30,.035,.035), rack_mat, .006)
    for x in (-.48,.64):
        box(f'HERO_CAB_RACK_FOOT_{side}_{x}', (x,side*.625,1.835), (.075,.060,.050), rack_mat, .005)
if LOD < 2:
    for i, x in enumerate((-.45,-.10,.25,.60)):
        box(f'HERO_CAB_RACK_CROSS_{i}', (x,0,rail_z+.002), (.032,1.31,.027), rack_mat, .004)

# Ditch-light housings in the reference are compact cubes. Legacy versions were
# visually ~6-inch blocks and dominated front 3/4 QA. Scale housings only; their
# mounting locations and role are unchanged.
for o in list(bpy.data.objects):
    if o.name.startswith('BLACK_OAK_'):
        o.scale *= .70

# Explicit UVs for all generated meshes keep the official ED material exporter
# contract intact. Primitive rack cubes already have UVs; this safely fills only
# meshes that do not.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons or len(obj.data.uv_layers):
        continue
    me = obj.data
    uv = me.uv_layers.new(name='UVMap')
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
    dx=max(xmax-xmin,1e-6); dy=max(ymax-ymin,1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=((co.x-xmin)/dx,(co.y-ymin)/dy)
    me.uv_layers.active=uv

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch12 complete: stock-like double-cab glass, cab-height long-bed topper, 2016 front composition and single low-profile rack; DCS mechanics untouched')
