import runpy
import bpy

# Geometry-only hero-body refinement layered on export-green patch21.
# Priority: double-cab rear greenhouse / C-pillar / cab-to-topper silhouette in side and rear-3Q clay QA.
# Preserve all proven DCS behavior, animation arguments, LOD/destroyed structure,
# official ED exporter pipeline, and one-folder Mods/tech packaging.
ns21 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch21.py', run_name='__main__')
LOD = ns21['LOD']
mesh_obj = ns21['mesh_obj']
curve_tube = ns21['curve_tube']
remove = ns21['remove']


def panel(name, verts, mat):
    return mesh_obj(name, verts, [tuple(range(len(verts)))], mat, True, 0.0)

paint = bpy.data.objects['HERO_HOOD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

# Idempotent cleanup for reruns.
for n in ('HERO_P22_REAR_ROOF_CAP','HERO_P22_REAR_ROOF_BREAK'):
    remove(n)
for side in (-1,1):
    for stem in ('HERO_P22_C_PILLAR_SKIN_','HERO_P22_C_PILLAR_EDGE_','HERO_P22_BELT_KICK_'):
        remove(f'{stem}{side}')

# The front greenhouse now has the correct taper, but the rear half still reads too
# wagon-like. Broaden the painted C-pillar at the belt, pull it inward toward the roof,
# and leave a cleaner vertical backlight boundary typical of the 2016 DCLB cab.
for side in (-1,1):
    s = side
    panel(f'HERO_P22_C_PILLAR_SKIN_{side}',[
        (-1.035,s*.715,1.130),(-1.035,s*.650,1.150),
        (-.900,s*.615,1.640),(-.825,s*.665,1.675),
        (-.850,s*.700,1.505),(-.945,s*.720,1.300)
    ],paint)
    if LOD < 2:
        curve_tube(f'HERO_P22_C_PILLAR_EDGE_{side}',[
            (-1.035,s*.716,1.145),(-.945,s*.720,1.300),(-.850,s*.700,1.505),(-.825,s*.665,1.675)
        ],.0055,black,1)

        # Tacoma-specific beltline rises slightly into the rear cab corner instead of
        # continuing as a dead-flat generic pickup crease.
        curve_tube(f'HERO_P22_BELT_KICK_{side}',[
            (-.520,s*.726,1.120),(-.760,s*.724,1.135),(-.960,s*.720,1.165),(-1.080,s*.710,1.205)
        ],.0050,black,1)

# Tie the rear roof into the revised C-pillars with a subtle crown and narrower trailing
# edge. This makes the cab read as a separate double-cab volume ahead of the topper.
panel('HERO_P22_REAR_ROOF_CAP',[
    (-.760,-.625,1.715),(-.825,-.665,1.675),(-1.020,-.620,1.690),
    (-1.075,0.0,1.735),(-1.020,.620,1.690),(-.825,.665,1.675),
    (-.760,.625,1.715),(-.720,0.0,1.755)
],paint)

if LOD < 2:
    curve_tube('HERO_P22_REAR_ROOF_BREAK',[
        (-.760,-.625,1.720),(-.900,-.640,1.705),(-1.075,0.0,1.740),
        (-.900,.640,1.705),(-.760,.625,1.720)
    ],.0045,black,1)

# Exporter UV safety for newly generated meshes.
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or not obj.data.polygons or len(obj.data.uv_layers):
        continue
    me = obj.data
    uv = me.uv_layers.new(name='UVMap')
    xs=[v.co.x for v in me.vertices]; ys=[v.co.y for v in me.vertices]
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
    dx=max(xmax-xmin,1e-6); dy=max(ymax-ymin,1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=((co.x-xmin)/dx,(co.y-ymin)/dy)
    me.uv_layers.active=uv

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch22 complete: broadened/tapered C-pillars, rear beltline kick, and crowned/narrowed rear roof for a more distinct 2016 DCLB cab-to-topper silhouette; DCS mechanics untouched')
