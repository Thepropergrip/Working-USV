import runpy
import bpy

# Geometry-only DCLB proportion pass layered on the exporter-green patch10.
# Keep the wheel rig, DCS registration/tuning, LOD/destroyed structure, exporter
# and package layout unchanged. This pass attacks the remaining box/van reading
# in side and 3/4 QA by reshaping only the cab greenhouse and long-bed topper.
ns10 = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch10.py', run_name='__main__')
base = ns10['ns']
LOD = ns10['LOD']
loft = base['loft']
panel = base['panel']
curve_tube = base['curve_tube']
remove = base['remove']

paint = bpy.data.objects['HERO_CAB_ROOF'].data.materials[0]
glass = bpy.data.objects['HERO_WINDSHIELD'].data.materials[0]
black = bpy.data.objects['HERO_B_PILLAR_1'].data.materials[0]

# Remove the current greenhouse/topper as a coherent set. The patch10 front
# clip remains untouched; this avoids disturbing the already-green exporter path.
for n in ('HERO_CAB_ROOF','HERO_WINDSHIELD','HERO_REAR_CAB_GLASS','HERO_CAMPER_SHELL','HERO_CAMPER_REAR_GLASS'):
    remove(n)
for side in (-1,1):
    for stem in ('HERO_FRONT_WINDOW_','HERO_REAR_WINDOW_','HERO_A_PILLAR_',
                 'HERO_B_PILLAR_','HERO_C_PILLAR_','HERO_WINDOW_SILL_',
                 'HERO_CAMPER_SIDE_GLASS_','HERO_CAMPER_TOP_FRAME_',
                 'HERO_CAMPER_BOTTOM_FRAME_','HERO_CAMPER_FRONT_FRAME_',
                 'HERO_CAMPER_REAR_FRAME_','HERO_CAMPER_DIVIDER_'):
        remove(stem + str(side))

# Third-gen Tacoma double-cab roof: a visibly longer crown, narrower upper
# greenhouse, slight rear taper, and a lower front brow. This removes the old
# rectangular roof block while retaining the actual DCLB door/window spacing.
def roof_ring(hw,zbase,zedge,zshoulder,crown):
    return [(-hw,zbase),(-hw,zedge),(-hw*.74,zshoulder),(-hw*.38,crown-.014),
            (0,crown),(hw*.38,crown-.014),(hw*.74,zshoulder),(hw,zedge),(hw,zbase)]

loft('HERO_CAB_ROOF',[
    (-.97,roof_ring(.640,1.575,1.635,1.720,1.765)),
    (-.78,roof_ring(.705,1.585,1.680,1.760,1.802)),
    (-.22,roof_ring(.735,1.590,1.700,1.780,1.820)),
    (.28,roof_ring(.720,1.580,1.685,1.760,1.800)),
    (.53,roof_ring(.650,1.545,1.625,1.700,1.748)),
],paint,.012)

# Windshield rake and upper width are tightened to the 2016 Tacoma greenhouse.
# Rear glass is nearly upright but not a vertical slab.
panel('HERO_WINDSHIELD',[(.88,-.820,1.145),(.88,.820,1.145),(.505,.645,1.690),(.505,-.645,1.690)],glass,.012)
panel('HERO_REAR_CAB_GLASS',[(-.955,.650,1.205),(-.955,-.650,1.205),(-.915,-.595,1.650),(-.915,.595,1.650)],glass,.012)

# Side glass now carries the Tacoma kick-up at the rear door and a more obvious
# A-pillar rake. The C-pillar leans forward slightly rather than reading as a van.
for side in (-1,1):
    yb=side*.925
    yt=side*.720
    panel(f'HERO_FRONT_WINDOW_{side}',[(.825,yb,1.185),(.045,yb,1.185),(.075,yt,1.650),(.485,side*.650,1.690)],glass,.010)
    panel(f'HERO_REAR_WINDOW_{side}',[(.010,yb,1.185),(-.790,yb,1.205),(-.875,side*.675,1.625),(.050,yt,1.650)],glass,.010)
    curve_tube(f'HERO_A_PILLAR_{side}',[(.855,side*.928,1.155),(.495,side*.665,1.705)],.024,paint,2)
    curve_tube(f'HERO_B_PILLAR_{side}',[(.030,side*.930,1.180),(.065,side*.725,1.670)],.028,black,1)
    curve_tube(f'HERO_C_PILLAR_{side}',[(-.805,side*.927,1.190),(-.900,side*.685,1.655)],.030,paint,2)
    curve_tube(f'HERO_WINDOW_SILL_{side}',[(-.810,side*.934,1.188),(.835,side*.934,1.178)],.015,black,1)

# Long-bed topper: lower than the cab crown, narrower at the roof, gently
# crowned, slightly tapered toward the rear, and with a clearly raked front cap.
# The lower belt stays aligned to the bed rails so this remains the user's custom
# shell rather than turning into an SUV body.
def cap_ring(hw,zbottom,zside,zshoulder,zcrown):
    return [(-hw,zbottom),(-hw,zside),(-hw*.73,zshoulder),(-hw*.34,zcrown-.012),
            (0,zcrown),(hw*.34,zcrown-.012),(hw*.73,zshoulder),(hw,zside),(hw,zbottom)]

loft('HERO_CAMPER_SHELL',[
    (-3.00,cap_ring(.735,1.180,1.430,1.555,1.610)),
    (-2.84,cap_ring(.795,1.180,1.475,1.610,1.665)),
    (-1.30,cap_ring(.805,1.180,1.490,1.625,1.680)),
    (-1.08,cap_ring(.720,1.180,1.410,1.540,1.600)),
],paint,.014)

for side in (-1,1):
    y=side*.820
    panel(f'HERO_CAMPER_SIDE_GLASS_{side}',[
        (-2.72,y,1.255),(-1.28,y,1.255),(-1.18,side*.770,1.575),(-2.64,side*.775,1.575)
    ],glass,.010)
    curve_tube(f'HERO_CAMPER_TOP_FRAME_{side}',[(-2.66,y,1.595),(-1.18,y,1.595)],.015,black,1)
    curve_tube(f'HERO_CAMPER_BOTTOM_FRAME_{side}',[(-2.72,y,1.245),(-1.27,y,1.245)],.015,black,1)
    curve_tube(f'HERO_CAMPER_FRONT_FRAME_{side}',[(-1.27,y,1.245),(-1.17,side*.775,1.590)],.016,black,1)
    curve_tube(f'HERO_CAMPER_REAR_FRAME_{side}',[(-2.72,y,1.245),(-2.64,side*.775,1.585)],.016,black,1)
    curve_tube(f'HERO_CAMPER_DIVIDER_{side}',[(-1.94,y,1.250),(-1.92,side*.790,1.590)],.013,black,1)

panel('HERO_CAMPER_REAR_GLASS',[(-3.012,-.650,1.245),(-3.012,.650,1.245),(-2.970,.570,1.570),(-2.970,-.570,1.570)],glass,.010)

# Add subtle roof drip rails; these give the side silhouette a real cab edge
# without accessory-level detailing.
for side in (-1,1):
    curve_tube(f'HERO_ROOF_DRIP_{side}',[(-.88,side*.682,1.690),(-.30,side*.728,1.748),(.31,side*.704,1.730),(.49,side*.650,1.688)],.009,black,1)

# All generated meshes need an explicit UV channel for the ED material exporter.
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
print('[TPG TACOMA] quality patch11 complete: longer tapered DCLB greenhouse and lower crowned long-bed topper; DCS mechanics untouched')
