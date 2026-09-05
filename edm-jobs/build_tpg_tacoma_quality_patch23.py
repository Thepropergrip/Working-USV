import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch22.
# Priority: front-fender shoulder / wheel-arch / hood-to-lamp transition in front and front-3Q clay QA.
# Preserve all proven DCS behavior, animation arguments, LOD/destroyed structure,
# official ED exporter pipeline, and one-folder Mods/tech packaging.
ns22 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch22.py', run_name='__main__')
LOD = ns22['LOD']
mesh_obj = ns22['mesh_obj']
curve_tube = ns22['curve_tube']
remove = ns22['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

# Idempotent cleanup for reruns.
for side in (-1, 1):
    for stem in ('HERO_P23_FENDER_CROWN_', 'HERO_P23_FENDER_ARCH_',
                 'HERO_P23_LAMP_BROW_', 'HERO_P23_SHOULDER_BREAK_'):
        remove(f'{stem}{side}')

# Third-gen Tacoma front quarters carry a distinct muscular crown above the front wheel,
# then pinch sharply inward toward the slim headlamp. Add that transition as a shallow
# painted skin so the nose reads sculpted rather than as a flat generic pickup box.
for side in (-1, 1):
    s = side
    panel(f'HERO_P23_FENDER_CROWN_{side}', [
        (1.02, s*.675, 1.185),
        (1.25, s*.760, 1.155),
        (1.58, s*.805, 1.105),
        (1.92, s*.790, 1.090),
        (2.22, s*.735, 1.115),
        (2.48, s*.610, 1.145),
        (2.34, s*.670, 1.185),
        (1.92, s*.730, 1.205),
        (1.35, s*.675, 1.205)
    ], paint)

    if LOD < 2:
        # A restrained wheel-arch eyebrow gives the front quarter the stamped Tacoma flare
        # visible in side/front-3Q without adding accessory-like thickness.
        curve_tube(f'HERO_P23_FENDER_ARCH_{side}', [
            (1.10, s*.776, .915),
            (1.20, s*.805, 1.020),
            (1.42, s*.826, 1.095),
            (1.68, s*.832, 1.125),
            (1.93, s*.815, 1.105),
            (2.12, s*.780, 1.045),
            (2.23, s*.742, .965)
        ], .0060, black, 2)

        # Slim high-mounted headlamp brow: continues the hood shoulder into the lamp corner
        # and prevents the fascia from reading as a tall square wall.
        curve_tube(f'HERO_P23_LAMP_BROW_{side}', [
            (2.20, s*.705, 1.175),
            (2.34, s*.670, 1.168),
            (2.49, s*.605, 1.150),
            (2.57, s*.525, 1.125)
        ], .0055, black, 1)

        # Longitudinal shoulder break ties the muscular fender into the previously revised
        # hood edge instead of leaving two unrelated masses.
        curve_tube(f'HERO_P23_SHOULDER_BREAK_{side}', [
            (1.05, s*.690, 1.175),
            (1.35, s*.735, 1.155),
            (1.72, s*.765, 1.130),
            (2.08, s*.748, 1.125),
            (2.34, s*.675, 1.155)
        ], .0045, black, 1)

# Exporter UV safety for newly generated meshes.
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
print('[TPG TACOMA] quality patch23 complete: stronger third-gen front-fender crown, wheel-arch flare, slim lamp brow and hood-to-fender shoulder transition; DCS mechanics untouched')
