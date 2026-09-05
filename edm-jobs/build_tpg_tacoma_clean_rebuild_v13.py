import bpy, os
from collections import defaultdict

# Tacoma FBX-v3 canonical final visual pass.
# Round 4 keeps the useful Round-3 cab/hood/topper sculpt but removes the proud
# fascia/hood appliques exposed by clay QA. Only thin flush 2016-style grille/lens
# inserts remain. Gameplay registration, tuning, wheel animation arguments,
# LOD/destroyed plumbing and the official exporter are untouched.

WHEEL_TARGETS = {
    "FBX_Cylinder_STEER":      ( 1.74, -0.805),
    "FBX_Cylinder.001_STEER": (-1.83, -0.805),
    "FBX_Cylinder.002_STEER": ( 1.74,  0.805),
    "FBX_Cylinder.003_STEER": (-1.83,  0.805),
}
for name, (tx, ty) in WHEEL_TARGETS.items():
    root = bpy.data.objects.get(name)
    if root is None:
        raise RuntimeError(f"Missing source-derived Tacoma wheel animation root: {name}")
    root.location.x = tx
    root.location.y = ty

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

stats = defaultdict(int)

# Bounded hero-body sculpt from measured QA bounds.
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)

    # Square roof shoulders while leaving doors, beltline and wheel arches source-derived.
    if -1.16 <= x <= 0.58 and 1.50 <= z <= 1.82 and 0.42 <= ay <= 0.70:
        tz = min(1.0, max(0.0, (z - 1.50) / 0.27))
        tx_rear = min(1.0, max(0.0, (x + 1.16) / 0.18))
        tx_front = min(1.0, max(0.0, (0.58 - x) / 0.18))
        fade = min(tx_rear, tx_front)
        desired_ay = min(0.725, ay + 0.065 * tz * fade)
        v.co.y = desired_ay if y >= 0 else -desired_ay
        stats["cab_shoulder_square"] += 1

    # Flatten the central roof crown to the broad third-gen Tacoma envelope.
    if -1.10 <= x <= 0.42 and z >= 1.765 and ay <= 0.62:
        edge = min(1.0, ay / 0.62)
        target_z = 1.807 - 0.010 * edge
        v.co.z += (target_z - v.co.z) * 0.78
        stats["roof_plane"] += 1

    # Straighten the windshield/header transition into a single defined rake.
    if 0.38 <= x <= 1.00 and 1.39 <= z <= 1.79:
        desired_x = 0.455 + (1.800 - z) * 1.18
        v.co.x += (desired_x - x) * 0.58
        stats["windshield_rake"] += 1

    # Broad smooth scoopless TRD Off-Road hood.
    if 1.04 <= x <= 2.50 and 1.02 <= z <= 1.36:
        tx = min(1.0, max(0.0, (x - 1.04) / 1.46))
        desired = 1.315 - 0.028 * tx
        blend = 0.58 if ay <= 0.68 else 0.24
        v.co.z += (desired - v.co.z) * blend
        stats["hood_plane"] += 1

    # Stand only the upper nose slightly more upright; preserve lower bumper geometry.
    if x >= 2.28 and 0.80 <= z <= 1.29:
        tx = min(1.0, max(0.0, (x - 2.28) / 0.44))
        tz = min(1.0, max(0.0, (z - 0.80) / 0.49))
        v.co.x += (0.010 + 0.014 * tz) * tx
        stats["nose"] += 1

# Equalize the hood center to local shoulder height at each x station so no scoop,
# recess or power bulge survives the original source topology.
stations = defaultdict(lambda: {"center": [], "shoulder": []})
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    if not (1.10 <= x <= 2.46 and 1.12 <= z <= 1.34):
        continue
    key = round(x / 0.035) * 0.035
    ay = abs(y)
    if ay <= 0.26:
        stations[key]["center"].append(v)
    elif 0.34 <= ay <= 0.62:
        stations[key]["shoulder"].append(v)
for group in stations.values():
    if not group["center"] or len(group["shoulder"]) < 2:
        continue
    zs = sorted(v.co.z for v in group["shoulder"])
    target = zs[len(zs)//2]
    for v in group["center"]:
        v.co.z += max(-0.014, min(0.014, (target - v.co.z) * 0.82))
        stats["hood_equalized"] += 1

body.data.update()

destroyed = os.environ.get("TPG_TACOMA_DESTROYED", "0") == "1"
paint = bpy.data.materials.get("TPG_TACOMA_Burnt" if destroyed else "TPG_TACOMA_Quicksand_4T8")
glass = bpy.data.materials.get("TPG_TACOMA_TintedGlass")
black = bpy.data.materials.get("TPG_TACOMA_Black")
lamp = bpy.data.materials.get("TPG_TACOMA_Lamp")
amber = bpy.data.materials.get("TPG_TACOMA_AmberLens")
if None in (paint, glass, black, lamp, amber):
    raise RuntimeError("Tacoma final-pass materials are missing")

def make_mesh(name, verts, faces, material, smooth=False, bevel=0.0):
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    me.materials.append(material)
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((co.x * 0.18 + co.y * 0.13) % 1.0,
                                  (co.z * 0.32 + co.y * 0.17) % 1.0)
    for p in me.polygons:
        p.use_smooth = smooth
    if bevel > 0.0:
        mod = obj.modifiers.new("edge_soften", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception:
            pass
    return obj

def prism_yz(name, poly, x_back, x_front, material, bevel=0.0):
    n = len(poly)
    verts = [(x_back, y, z) for y,z in poly] + [(x_front, y, z) for y,z in poly]
    faces = [tuple(range(n-1, -1, -1)), tuple(n+i for i in range(n))]
    for i in range(n):
        j = (i+1) % n
        faces.append((i, j, n+j, n+i))
    return make_mesh(name, verts, faces, material, smooth=False, bevel=bevel)

# Remove every older generated shell/fascia object before creating the final set.
for obj in list(bpy.data.objects):
    if obj.name.startswith(("CAMPER_BODY", "CAMPER_ROOF", "CAMPER_SIDE_GLASS_",
                            "CAMPER_REAR_GLASS", "CAMPER_HERO_SHELL_", "TPG_FINAL_")):
        bpy.data.objects.remove(obj, do_unlink=True)

# Lower, straighter ARE-style long-bed topper: near cab-height roof, nearly vertical
# side walls and shallow shoulders matching the reference truck.
stations_shell = [
    (-1.08, 0.985,  0.000),
    (-1.48, 1.000,  0.002),
    (-2.18, 1.000,  0.000),
    (-2.68, 0.975, -0.010),
]
profile = [
    (-0.862,1.000),(-0.862,1.440),(-0.850,1.650),(-0.815,1.748),
    (-0.755,1.790),(-0.625,1.807),(0.625,1.807),(0.755,1.790),
    (0.815,1.748),(0.850,1.650),(0.862,1.440),(0.862,1.000),
]
verts = []
for x, scale, roof_add in stations_shell:
    for y,z in profile:
        t = max(0.0, min(1.0, (z-1.60)/0.22))
        verts.append((x, y*scale, z + roof_add*t))
n = len(profile)
faces = []
for s in range(len(stations_shell)-1):
    a,b = s*n,(s+1)*n
    for i in range(n-1):
        faces.append((a+i,a+i+1,b+i+1,b+i))
faces.append(tuple(range(n-1,-1,-1)))
r0=(len(stations_shell)-1)*n
faces.append(tuple(r0+i for i in range(n)))
make_mesh("CAMPER_HERO_SHELL_V16", verts, faces, paint, smooth=True, bevel=0.010)

for side in (-1,1):
    y=side*0.853
    win=[
        (-2.49,y,1.245),(-2.49,y,1.630),(-2.39,y,1.724),
        (-1.34,y,1.724),(-1.24,y,1.674),(-1.21,y,1.245)
    ]
    face=[tuple(range(len(win)))] if side>0 else [tuple(range(len(win)-1,-1,-1))]
    make_mesh(f"CAMPER_SIDE_GLASS_HERO_{side}",win,face,glass,smooth=False)
rear_x=-2.690
rear=[
    (rear_x,-0.670,1.235),(rear_x,0.670,1.235),(rear_x,0.670,1.620),
    (rear_x,0.595,1.718),(rear_x,-0.595,1.718),(rear_x,-0.670,1.620)
]
make_mesh("CAMPER_REAR_GLASS_HERO",rear,[tuple(range(len(rear)))],glass,smooth=False)

# Round-4 fascia integration: no hood skin, no paint surround and no thick backing
# blocks. Only millimeter-thin inserts sit essentially flush with the source nose.
grille=[(-0.625,1.205),(0.625,1.205),(0.535,0.965),(-0.535,0.965)]
prism_yz("TPG_FINAL_GRILLE", grille, 2.706, 2.714, black, bevel=0.006)
for i,z in enumerate((1.155,1.085,1.015)):
    bar=[(-0.565,z+0.008),(0.565,z+0.008),(0.545,z-0.008),(-0.545,z-0.008)]
    prism_yz(f"TPG_FINAL_GRILLE_BAR_{i}", bar, 2.714, 2.717, black, bevel=0.0015)

for side in (-1,1):
    if side>0:
        lens=[(0.650,1.215),(0.900,1.185),(0.885,1.095),(0.675,1.110)]
        amb=[(0.870,1.177),(0.905,1.168),(0.895,1.108),(0.862,1.112)]
    else:
        lens=[(-0.900,1.185),(-0.650,1.215),(-0.675,1.110),(-0.885,1.095)]
        amb=[(-0.905,1.168),(-0.870,1.177),(-0.862,1.112),(-0.895,1.108)]
    prism_yz(f"TPG_FINAL_HEADLIGHT_{side}", lens, 2.708, 2.716, lamp, bevel=0.002)
    prism_yz(f"TPG_FINAL_HEADLIGHT_AMBER_{side}", amb, 2.716, 2.719, amber, bevel=0.001)

# Ditch-light housings were oversized relative to the user's reference photos.
for obj in bpy.data.objects:
    if obj.name.startswith("BLACK_OAK_"):
        obj.scale *= 0.72

print("[TPG TACOMA ROUND4 FINAL] retained Round-3 body/topper gains; removed proud hood/fascia "
      "appliques and integrated flush 2016 grille/headlamp inserts", dict(stats))
