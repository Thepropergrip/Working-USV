import runpy, os
import bpy

# Build the full v6 photo-derived truck, then correct the one geometry choice that
# made the authoritative clay render look like a rectangular van: HERO_BODY_CORE
# was a full-height 5.5 m extrusion spanning nose-to-tail.  Retain the detailed
# v6 fenders, cab, hood, topper, glazing, grille, lamps and validated FBX wheels,
# but replace that core with a low structural underbody that cannot mask the
# actual Tacoma silhouette.
ns = runpy.run_path('edm-jobs/build_tpg_tacoma_quality_patch6.py', run_name='__main__')
M = ns['M']
LOD = ns['LOD']
DESTROYED = os.environ.get('TPG_TACOMA_DESTROYED', '0') == '1'
loft = ns['loft']
prism_xz = ns['prism_xz']
curve_tube = ns['curve_tube']
paint = M['burnt'] if DESTROYED else M['paint']
black = M['black']
metal = M['metal']


def remove_exact(name):
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)


def remove_prefix(prefix):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


# Remove the v6 slab responsible for the false van-like clay render.
remove_exact('HERO_BODY_CORE')

# Low, tapered central body/chassis volume.  It provides visual continuity only
# below the beltline while allowing the independently modeled DCLB cab, wheel
# arches, hood, bed and topper to define the visible silhouette.
low_ring_rear = [(-0.66,0.48),(-0.66,0.66),(-0.52,0.76),(0.52,0.76),(0.66,0.66),(0.66,0.48)]
low_ring_mid  = [(-0.70,0.46),(-0.70,0.72),(-0.56,0.82),(0.56,0.82),(0.70,0.72),(0.70,0.46)]
low_ring_front= [(-0.62,0.47),(-0.62,0.68),(-0.50,0.78),(0.50,0.78),(0.62,0.68),(0.62,0.47)]
loft('HERO_UNDERBODY_CORE', [(-2.88,low_ring_rear),(-0.92,low_ring_mid),(0.82,low_ring_mid),(2.52,low_ring_front)], paint, True, .018)

# Add narrow rocker/floor closures rather than a full-height side wall.
for side in (-1, 1):
    prism_xz(f'HERO_ROCKER_CLOSURE_{side}', [(-2.78,.50),(-2.78,.67),(2.40,.67),(2.50,.57),(2.46,.50)], side*.835, .055, paint, .012)

# The user's truck has a single low-profile rack over the cab.  Remove the two
# legacy racks inherited from the early generic build, then create one compact
# cab-only platform aligned with the reference photos/concept sheet.
remove_prefix('RACK_RAIL_')
remove_prefix('RACK_BAR_')
remove_prefix('HERO_CAB_RACK_')

rack_z = 1.885
for side in (-1, 1):
    curve_tube(f'HERO_CAB_RACK_SIDE_{side}', [(-.62,side*.70,rack_z),(.50,side*.70,rack_z)], .022, metal, 1)
for i in range(7 if LOD == 0 else (5 if LOD == 1 else 3)):
    x = -.58 + 1.04 * i / ((7 if LOD == 0 else (5 if LOD == 1 else 3)) - 1)
    curve_tube(f'HERO_CAB_RACK_CROSS_{i}', [(x,-.69,rack_z),(x,.69,rack_z)], .018, metal, 1)
for x in (-.58,.46):
    for side in (-1,1):
        curve_tube(f'HERO_CAB_RACK_FOOT_{x}_{side}', [(x,side*.64,1.79),(x,side*.69,rack_z)], .020, metal, 1)

# Subtle lower grille opening/air gap so the front clip reads as a Tacoma in clay
# instead of one continuous planar block.
for side in (-1,1):
    curve_tube(f'HERO_LOWER_BUMPER_BREAK_{side}', [(2.735,side*.60,.735),(2.735,side*.28,.705)], .010, black, 0)
curve_tube('HERO_LOWER_BUMPER_BREAK_CENTER', [(2.738,-.30,.705),(2.738,.30,.705)], .010, black, 0)

bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch7 complete: slab core removed, tapered low underbody installed, single low-profile cab rack enforced')
