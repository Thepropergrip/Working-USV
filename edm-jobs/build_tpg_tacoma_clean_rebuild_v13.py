import bpy, os
from collections import defaultdict

# Tacoma FBX-v3 canonical final visual pass.
# Round 3 is a bounded closeout sculpt based on the dedicated Round-2 clay QA and
# the 2016 Tacoma TRD Off Road DCLB concept/reference sheet. Gameplay registration,
# tuning, wheel animation arguments, LOD/destroyed plumbing and exporter are untouched.

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

# First pass: force the upper greenhouse into the broad, flatter third-gen Tacoma
# envelope while leaving doors, beltline, wheel arches and bed untouched.
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)

    # Square roof shoulders more decisively than Round 2. Only the upper cab is touched.
    if -1.16 <= x <= 0.58 and 1.50 <= z <= 1.82 and 0.42 <= ay <= 0.70:
        tz = min(1.0, max(0.0, (z - 1.50) / 0.27))
        tx_rear = min(1.0, max(0.0, (x + 1.16) / 0.18))
        tx_front = min(1.0, max(0.0, (0.58 - x) / 0.18))
        fade = min(tx_rear, tx_front)
        desired_ay = ay + 0.065 * tz * fade
        desired_ay = min(0.725, desired_ay)
        v.co.y = desired_ay if y >= 0 else -desired_ay
        stats["cab_shoulder_square"] += 1

    # Flatten the roof crown to a shallow plane. Preserve a few millimeters of crown,
    # but remove the continuous dome seen in Round-2 side/front-3Q clay.
    if -1.10 <= x <= 0.42 and z >= 1.765 and ay <= 0.62:
        edge = min(1.0, ay / 0.62)
        target_z = 1.807 - 0.010 * edge
        v.co.z += (target_z - v.co.z) * 0.78
        stats["roof_plane"] += 1

    # Straighten the upper windshield/header into a single Tacoma-like rake instead of
    # the source mesh's rounded transition. Blend to a measured side-profile line.
    if 0.38 <= x <= 1.00 and 1.39 <= z <= 1.79:
        desired_x = 0.455 + (1.800 - z) * 1.18
        v.co.x += (desired_x - x) * 0.58
        stats["windshield_rake"] += 1

    # Broad, smooth, scoopless Off-Road hood. Reduce center/shoulder waviness and keep
    # the hood below the greenhouse; no Sport scoop or power bulge.
    if 1.04 <= x <= 2.50 and 1.02 <= z <= 1.36:
        tx = min(1.0, max(0.0, (x - 1.04) / 1.46))
        desired = 1.315 - 0.028 * tx
        # Preserve fender shoulders more than the central hood skin.
        blend = 0.58 if ay <= 0.68 else 0.24
        v.co.z += (desired - v.co.z) * blend
        stats["hood_plane"] += 1

    # Slightly stand the upper nose up; lower bumper geometry stays source-derived.
    if x >= 2.28 and 0.80 <= z <= 1.29:
        tx = min(1.0, max(0.0, (x - 2.28) / 0.44))
        tz = min(1.0, max(0.0, (z - 0.80) / 0.49))
        v.co.x += (0.010 + 0.014 * tz) * tx
        stats["nose"] += 1

# Second hood pass: equalize center vertices to local shoulder median at the same x.
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
    # poly is [(y,z), ...] in front-view winding.
    n = len(poly)
    verts = [(x_back, y, z) for y,z in poly] + [(x_front, y, z) for y,z in poly]
    faces = [tuple(range(n-1, -1, -1)), tuple(n+i for i in range(n))]
    for i in range(n):
        j = (i+1) % n
        faces.append((i, j, n+j, n+i))
    return make_mesh(name, verts, faces, material, smooth=False, bevel=bevel)

# Replace every prior procedural camper shell with a lower, straighter ARE-style cap.
for obj in list(bpy.data.objects):
    if obj.name.startswith(("CAMPER_BODY","CAMPER_ROOF","CAMPER_SIDE_GLASS_",
                            "CAMPER_REAR_GLASS","CAMPER_HERO_SHELL_",
                            "TPG_FINAL_")):
        bpy.data.objects.remove(obj, do_unlink=True)

stations_shell = [
    (-1.08, 0.985,  0.000),
    (-1.48, 1.000,  0.002),
    (-2.18, 1.000,  0.000),
    (-2.68, 0.975, -0.010),
]
# Flatter roof, more vertical sides, tighter shoulders; roof essentially flush with cab.
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

# Thin scoopless hood skin. This covers source waviness/slotting without changing
# collision or wheel openings and gives the front-3Q silhouette a clean factory hood.
hood_top = [
    (1.15,-0.825,1.318),(1.15,0.825,1.318),
    (2.53,0.770,1.286),(2.53,-0.770,1.286),
]
hood_bot = [(x,y,z-0.010) for x,y,z in hood_top]
verts = hood_bot + hood_top
faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
make_mesh("TPG_FINAL_HOOD_SKIN",verts,faces,paint,smooth=False,bevel=0.006)

# 2016 Tacoma face: paint trapezoid surround, black hex/trapezoid grille and compact
# swept headlamp blocks. These are visual appliques placed just ahead of the source face.
outer=[(-0.705,1.255),(0.705,1.255),(0.610,0.915),(-0.610,0.915)]
prism_yz("TPG_FINAL_GRILLE_FRAME",outer,2.704,2.726,paint,bevel=0.018)
inner=[(-0.630,1.205),(0.630,1.205),(0.535,0.965),(-0.535,0.965)]
prism_yz("TPG_FINAL_GRILLE",inner,2.727,2.742,black,bevel=0.012)

# Three subtle horizontal grille bars.
for i,z in enumerate((1.155,1.085,1.015)):
    poly=[(-0.575,z+0.012),(0.575,z+0.012),(0.555,z-0.012),(-0.555,z-0.012)]
    prism_yz(f"TPG_FINAL_GRILLE_BAR_{i}",poly,2.742,2.748,black,bevel=0.003)

for side in (-1,1):
    # Headlight backing and inset lens, swept upward toward fender.
    if side>0:
        back=[(0.625,1.235),(0.915,1.205),(0.900,1.080),(0.655,1.095)]
        lens=[(0.655,1.210),(0.880,1.185),(0.865,1.105),(0.675,1.115)]
        amb=[(0.865,1.175),(0.905,1.168),(0.895,1.105),(0.855,1.110)]
    else:
        back=[(-0.915,1.205),(-0.625,1.235),(-0.655,1.095),(-0.900,1.080)]
        lens=[(-0.880,1.185),(-0.655,1.210),(-0.675,1.115),(-0.865,1.105)]
        amb=[(-0.905,1.168),(-0.865,1.175),(-0.855,1.110),(-0.895,1.105)]
    prism_yz(f"TPG_FINAL_HEADLIGHT_BACK_{side}",back,2.704,2.730,black,bevel=0.006)
    prism_yz(f"TPG_FINAL_HEADLIGHT_{side}",lens,2.731,2.744,lamp,bevel=0.004)
    prism_yz(f"TPG_FINAL_HEADLIGHT_AMBER_{side}",amb,2.744,2.750,amber,bevel=0.002)

# Ditch lights in the source build were visually oversized in clay. Scale only their
# meshes, keeping mounts and positions intact.
for obj in bpy.data.objects:
    if obj.name.startswith("BLACK_OAK_"):
        obj.scale *= 0.72

print("[TPG TACOMA ROUND3 FINAL] squared cab, straightened windshield, scoopless hood skin, "
      "2016 front face and lower ARE-style topper applied", dict(stats))
