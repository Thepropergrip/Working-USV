import bpy, os
from collections import defaultdict

# Canonical Tacoma photo-match pass.
# IMPORTANT: This is intentionally ONE source-mesh-derived body pass from FBX_Plane.001.
# It replaces the old V13->V17 cumulative deformation chain. All body corrections use
# bounded/absolute target envelopes so they do not compound across releases.
# DCS wheel hierarchy, arg 8 wheel roll, arg 9 steering, gameplay tuning, collision,
# LOD/destroyed structure, materials, registration and official ED exporter are untouched.

body = bpy.data.objects.get("FBX_Plane.001")
if body is None or body.type != 'MESH':
    raise RuntimeError("Missing source-derived Tacoma body FBX_Plane.001")

stats = defaultdict(int)
for v in body.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    ay = abs(y)
    sign = 1.0 if y >= 0.0 else -1.0

    # 2016 DCLB cab: broad, nearly flat roof and defined roof shoulders.
    if -1.12 <= x <= 0.48 and z >= 1.70 and ay <= 0.74:
        edge = min(1.0, ay / 0.70)
        target_z = 1.812 - 0.012 * edge
        v.co.z += max(-0.018, min(0.018, (target_z - z) * 0.72))
        if 0.50 <= ay <= 0.72:
            target_y = sign * min(0.725, max(ay, 0.655 + 0.060 * max(0.0, (z-1.70)/0.12)))
            v.co.y += (target_y - y) * 0.62
        stats["roof"] += 1

    # Narrower greenhouse above the beltline; do not move lower doors/rockers.
    if -0.76 <= x <= 1.18 and 1.34 <= z <= 1.68 and 0.58 <= ay <= 0.90:
        edge_x = min(1.0, max(0.0, (x + 0.76)/0.22), max(0.0, (1.18-x)/0.22))
        edge_z = min(1.0, max(0.0, (z-1.34)/0.11), max(0.0, (1.68-z)/0.12))
        target_ay = max(0.56, ay - 0.030 * edge_x * edge_z)
        v.co.y = sign * target_ay
        stats["greenhouse"] += 1

    # Defined beltline shoulder under the glasshouse.
    if -0.74 <= x <= 1.26 and 1.22 <= z <= 1.34 and 0.60 <= ay <= 0.91:
        fz = 1.0 - min(1.0, abs(z - 1.28)/0.06)
        target_ay = min(0.925, ay + 0.012 * fz)
        v.co.y = sign * target_ay
        stats["beltline"] += 1

    # One deliberate windshield rake from cowl to roof; absolute target, not additive.
    if 0.48 <= x <= 1.18 and 1.42 <= z <= 1.78 and 0.42 <= ay <= 0.84:
        target_x = 0.49 + (1.80 - z) * 1.28
        blend = 0.50 * (1.0 - min(1.0, abs(ay-0.64)/0.24))
        v.co.x += max(-0.055, min(0.055, (target_x - x) * blend))
        stats["windshield"] += 1

    # Clean cowl break so hood and windshield do not read as one continuous ramp.
    if 1.08 <= x <= 1.50 and 1.28 <= z <= 1.45 and ay <= 0.80:
        fx = 1.0 - min(1.0, abs(x-1.29)/0.21)
        v.co.z -= 0.006 * fx
        stats["cowl"] += 1

    # Scoopless TRD Off-Road hood: broad plane with mild forward fall.
    if 1.08 <= x <= 2.46 and 1.08 <= z <= 1.37 and ay <= 0.76:
        tx = min(1.0, max(0.0, (x-1.08)/1.38))
        target_z = 1.315 - 0.026 * tx
        blend = 0.62 if ay <= 0.28 else 0.36
        v.co.z += max(-0.018, min(0.018, (target_z-z)*blend))
        stats["hood"] += 1

    # Broad hood/fender shoulders, strongest ahead of the A-pillar but fading at nose.
    if 1.50 <= x <= 2.34 and 1.10 <= z <= 1.36 and 0.48 <= ay <= 0.88:
        fx = min(1.0, max(0.0, (x-1.50)/0.60))
        fy = 1.0 - min(1.0, abs(ay-0.70)/0.22)
        target_ay = min(0.90, ay + 0.016*fx*fy)
        v.co.y = sign * target_ay
        stats["front_shoulders"] += 1

    # Preserve source lower bumper; only stand the lamp/grille band slightly upright.
    if x >= 2.36 and 0.96 <= z <= 1.26 and ay <= 0.91:
        v.co.x += 0.006 * (0.65 + 0.35*min(1.0, max(0.0, (z-0.96)/0.30)))
        stats["upper_nose"] += 1

    # Square rear cab upper station for DCLB silhouette.
    if -1.22 <= x <= -0.92 and 1.42 <= z <= 1.76 and ay <= 0.80:
        target_x = -1.11 - 0.010*min(1.0, max(0.0, (z-1.42)/0.34))
        v.co.x += max(-0.010, min(0.010, (target_x-x)*0.30))
        stats["rear_cab"] += 1

body.data.update()

# Rebuild only the camper shell as a clean low-profile ARE-style long-bed cap.
destroyed = os.environ.get("TPG_TACOMA_DESTROYED", "0") == "1"
paint = bpy.data.materials.get("TPG_TACOMA_Burnt" if destroyed else "TPG_TACOMA_Quicksand_4T8")
glass = bpy.data.materials.get("TPG_TACOMA_TintedGlass")
if paint is None or glass is None:
    raise RuntimeError("Tacoma canonical materials missing")

for obj in list(bpy.data.objects):
    if obj.name.startswith(("CAMPER_BODY","CAMPER_ROOF","CAMPER_SIDE_GLASS_","CAMPER_REAR_GLASS","CAMPER_HERO_SHELL_")):
        bpy.data.objects.remove(obj, do_unlink=True)

def mesh_obj(name, verts, faces, mat, smooth=False):
    me=bpy.data.meshes.new(name+"_mesh"); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob); me.materials.append(mat)
    for p in me.polygons: p.use_smooth=smooth
    return ob

stations=[(-1.08,0.985,0.000),(-1.48,1.000,0.002),(-2.18,1.000,0.000),(-2.68,0.975,-0.010)]
profile=[(-0.862,1.00),(-0.862,1.44),(-0.850,1.65),(-0.815,1.748),(-0.755,1.790),(-0.625,1.807),(0.625,1.807),(0.755,1.790),(0.815,1.748),(0.850,1.65),(0.862,1.44),(0.862,1.00)]
verts=[]
for sx,scale,ra in stations:
    for py,pz in profile:
        t=max(0.0,min(1.0,(pz-1.60)/0.22)); verts.append((sx,py*scale,pz+ra*t))
n=len(profile); faces=[]
for s in range(len(stations)-1):
    a,b=s*n,(s+1)*n
    for i in range(n-1): faces.append((a+i,a+i+1,b+i+1,b+i))
faces.append(tuple(range(n-1,-1,-1))); r0=(len(stations)-1)*n; faces.append(tuple(r0+i for i in range(n)))
mesh_obj("CAMPER_HERO_SHELL_CANONICAL",verts,faces,paint,True)
for side in (-1,1):
    yy=side*0.853
    win=[(-2.49,yy,1.245),(-2.49,yy,1.630),(-2.39,yy,1.724),(-1.34,yy,1.724),(-1.24,yy,1.674),(-1.21,yy,1.245)]
    mesh_obj(f"CAMPER_SIDE_GLASS_CANONICAL_{side}",win,[tuple(range(6)) if side>0 else tuple(range(5,-1,-1))],glass,False)
rear_x=-2.690
rear=[(rear_x,-0.670,1.235),(rear_x,0.670,1.235),(rear_x,0.670,1.620),(rear_x,0.595,1.718),(rear_x,-0.595,1.718),(rear_x,-0.670,1.620)]
mesh_obj("CAMPER_REAR_GLASS_CANONICAL",rear,[tuple(range(6))],glass,False)

print("[TPG TACOMA CANONICAL PHOTO MATCH] single source-FBX body pass complete", dict(stats))
