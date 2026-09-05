import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch26.
# Priority: third-gen Tacoma front-fender / bumper-to-wheel-opening silhouette in front/front-3Q clay QA.
# Preserve proven DCS mechanics, animation arguments, LOD/destroyed structure,
# official ED exporter pipeline, and one-folder Mods/tech packaging.
ns26 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch26.py', run_name='__main__')
LOD = ns26['LOD']
mesh_obj = ns26['mesh_obj']
curve_tube = ns26['curve_tube']
remove = ns26['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

for side in (-1, 1):
    for stem in ('HERO_P27_FENDER_CROWN_', 'HERO_P27_ARCH_LIP_', 'HERO_P27_BUMPER_ARCH_RETURN_', 'HERO_P27_HOOD_FENDER_BREAK_'):
        remove(f'{stem}{side}')

for side in (-1, 1):
    s = side

    # Build a stronger Tacoma-like outer fender shoulder from the lamp sweep back over the
    # front wheel opening. The crown sits proud at the lamp corner and relaxes rearward,
    # avoiding the slab-sided/generic pickup read in front-3Q.
    panel(f'HERO_P27_FENDER_CROWN_{side}', [
        (2.39,s*.790,1.120), (2.25,s*.865,1.145), (2.02,s*.905,1.155),
        (1.73,s*.925,1.145), (1.47,s*.920,1.105), (1.38,s*.900,1.040),
        (1.55,s*.875,1.080), (1.82,s*.865,1.105), (2.10,s*.850,1.110)
    ], paint)

    # Clamp-shaped bumper wing now resolves into the wheel opening instead of terminating
    # as an isolated front panel. This gives the lower front clip a continuous sculpted return.
    panel(f'HERO_P27_BUMPER_ARCH_RETURN_{side}', [
        (2.50,s*.765,.900), (2.38,s*.815,.865), (2.20,s*.850,.825),
        (2.02,s*.865,.790), (1.90,s*.860,.755), (2.02,s*.830,.730),
        (2.22,s*.805,.755), (2.40,s*.780,.805)
    ], paint)

    if LOD < 2:
        # A restrained dark arch lip makes the wheel opening read cleanly in clay renders
        # without spending this pass on trim/accessory detail.
        curve_tube(f'HERO_P27_ARCH_LIP_{side}', [
            (1.42,s*.904,1.020), (1.48,s*.918,.900), (1.60,s*.925,.790),
            (1.78,s*.930,.725), (1.98,s*.925,.735), (2.15,s*.910,.805),
            (2.28,s*.885,.900)
        ], .0070, black, 2)

        # Carry the hood shoulder into the outer fender crown so the upper front clip reads
        # as one stamped Tacoma form rather than separate hood and side boxes.
        curve_tube(f'HERO_P27_HOOD_FENDER_BREAK_{side}', [
            (2.30,s*.505,1.218), (2.20,s*.610,1.205), (2.08,s*.720,1.190),
            (1.95,s*.805,1.175), (1.80,s*.865,1.155)
        ], .0055, black, 1)

# Exporter UV safety for newly generated visible meshes.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons or len(obj.data.uv_layers):
        continue
    me = obj.data
    uv = me.uv_layers.new(name='UVMap')
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
    dx = max(xmax-xmin, 1e-6); dy = max(ymax-ymin, 1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co.x-xmin)/dx, (co.y-ymin)/dy)
    me.uv_layers.active = uv

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch27 complete: front fender crown, wheel-opening lip, bumper-to-arch return and hood/fender break; DCS mechanics untouched')
