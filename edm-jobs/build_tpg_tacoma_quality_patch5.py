import runpy, math
import bpy

# Build from the last validated wheel-parenting baseline exactly once. Patch4
# now deliberately re-exports patch3's helper namespace so this pass can add
# detail without constructing a second Tacoma on top of the first.
ns = runpy.run_path("edm-jobs/build_tpg_tacoma_quality_patch4.py", run_name="__main__")
M = ns['M']; box = ns['box']; cyl = ns['cyl']; torus = ns['torus']
LOD = ns['LOD']

# ---------------------------------------------------------------------------
# Visual-fidelity pass: only equipment visible in the supplied truck photos.
# No weapons, antennas, snorkels, winches, roof tents, or other invented gear.
# ---------------------------------------------------------------------------

# Camper shell: soften the previously boxy presentation with real topper cues,
# while retaining the paint-matched long-bed shell already established.
for s in (-1, 1):
    y = s * .885
    box(f'CAMPER_FRAME_TOP_{s}', (-1.82, y, 1.675), (1.30, .020, .026), M['black'], .005)
    box(f'CAMPER_FRAME_BOTTOM_{s}', (-1.82, y, 1.265), (1.30, .020, .026), M['black'], .005)
    box(f'CAMPER_FRAME_FRONT_{s}', (-1.18, y, 1.47), (.026, .020, .42), M['black'], .004)
    box(f'CAMPER_FRAME_REAR_{s}', (-2.46, y, 1.47), (.026, .020, .42), M['black'], .004)
box('CAMPER_HATCH_TOP', (-2.675, 0, 1.675), (.020, 1.47, .026), M['black'], .004)
for s in (-1,1):
    box(f'CAMPER_HATCH_SIDE_{s}', (-2.675, s*.724, 1.47), (.020, .026, .42), M['black'], .004)
box('CAMPER_HATCH_HANDLE', (-2.690, 0, 1.205), (.025, .20, .035), M['black'], .008)

# Cab rack: retain one low-profile rack only. Patch3 already removes the
# invented camper rack; remove stray cab slats so the silhouette stays shallow.
for o in list(bpy.data.objects):
    if o.name.startswith('RACK_BAR_0.25_'):
        try:
            idx = int(o.name.rsplit('_',1)[-1])
        except Exception:
            idx = -1
        if idx not in (0,2,3,5):
            bpy.data.objects.remove(o, do_unlink=True)
box('CAB_RACK_FRONT_RAIL', (.84, 0, 1.89), (.055, 1.53, .055), M['metal'], .010)
box('CAB_RACK_REAR_RAIL', (-.34, 0, 1.89), (.055, 1.53, .055), M['metal'], .010)

# Black Oak forward ditch lights: square finned housings, black bezels and
# visible mounting feet/bolts. Existing four LED emitters remain intact.
for s in (-1, 1):
    y = s * .89
    box(f'BLACK_OAK_BEZEL_{s}', (1.176, y, 1.49), (.020, .184, .164), M['black'], .012)
    box(f'BLACK_OAK_BRACKET_FOOT_{s}', (1.02, s*.80, 1.355), (.085, .065, .025), M['metal'], .006)
    cyl(f'BLACK_OAK_BRACKET_BOLT_{s}', (1.02, s*.806, 1.368), .015, .014, M['alloy'], 16, rot=(math.pi/2,0,0))

# Slim lower-grille LED bar with segmented emitters.
box('FRONT_LED_BAR_BEZEL', (2.778, 0, .555), (.012, 1.16, .070), M['black'], .006)
if LOD == 0:
    for i in range(12):
        y = -.99 + i*(1.98/11.0)
        box(f'FRONT_LED_CELL_{i}', (2.788, y, .555), (.006, .105, .040), M['aux_led'], .003)

# Custom rear bumper with center inset and correctly amber reverse lamps.
box('REAR_BUMPER_CENTER_INSET', (-3.000, 0, .615), (.022, .78, .145), M['black'], .018)
for s in (-1,1):
    box(f'REAR_BUMPER_SEAM_{s}', (-2.995, s*.72, .655), (.025, .018, .235), M['black'], .003)
    box(f'REAR_AMBER_BEZEL_{s}', (-3.008, s*.56, .69), (.010, .225, .112), M['black'], .008)
    box(f'REAR_AMBER_LENS_FACE_{s}', (-3.016, s*.56, .69), (.006, .184, .074), M['aux_amber'], .006)

# Rock-slider outer rail end caps keep close side views from reading as open
# procedural tubes.
for s in (-1,1):
    for x in (-1.05, 1.02):
        cyl(f'SLIDER_ENDCAP_{s}_{x}', (x, s*1.0, .53), .041, .018, M['metal'], 20, rot=(0,math.pi/2,0))

# Preserve the validated neutral export state. No wheel-rig topology changes in
# this pass; argument 8 roll and argument 9 front steering remain untouched.
bpy.context.scene.frame_set(100)
print('[TPG TACOMA] quality patch5 complete: single-scene topper/rack/ditch-light/LED-bar/rear-bumper fidelity pass')
