import bpy, math, os, random, zlib
from pathlib import Path
from mathutils import Vector

# TPG Warzone Rubble Pile 01
# PR validation trigger: Windows Blender 4.1.1 / official ED exporter
# 20 x 20 ft class rubble/debris static asset for DCS World.
# No terrain/base plane is used: low debris is deliberately buried slightly below z=0
# so the pile integrates into DCS terrain without a coplanar slab or z-fighting.

WORK = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
TEXDIR = WORK / "edm-artifacts" / "Textures"
TEXDIR.mkdir(parents=True, exist_ok=True)

from materials.materials import build_material_descriptions
from materials.material_tools import createEdmNodeGroup
from enums import NodeSocketInDefaultEnum
from objects_custom_props import get_edm_props

MAT_DESCS = build_material_descriptions()
MATS = {}

VARIANT = os.environ.get("TPG_RUBBLE_VARIANT", "intact").lower()
DESTROYED = VARIANT == "destroyed"
LOD = 1 if VARIANT == "lod1" else (2 if VARIANT == "lod2" else 0)

SEED = 93012026 + (700 if DESTROYED else 0) + LOD * 100
RNG = random.Random(SEED)


def clamp(v):
    return max(0.0, min(1.0, v))


def _tex(name, base, rough_pattern="generic", size=256):
    path = TEXDIR / (name + ".png")
    if path.exists():
        return path
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    rng = random.Random(zlib.crc32(name.encode("utf-8")) & 0xffffffff)
    px = []
    for y in range(size):
        v = y / max(1, size - 1)
        for x in range(size):
            u = x / max(1, size - 1)
            n = (rng.random() - .5)
            r, g, b = base
            if rough_pattern == "concrete":
                grain = n * .075 + .018 * math.sin(x * .29) + .012 * math.sin(y * .17)
                if rng.random() < .032:
                    grain += rng.choice((-1, 1)) * rng.uniform(.08, .18)
                stains = .025 * (math.sin(u * 17.0 + v * 9.0) + math.sin(v * 23.0))
                r += grain - stains; g += grain - stains; b += grain - stains
            elif rough_pattern == "rust":
                grain = n * .11
                mott = .08 * math.sin(u * 25.0) * math.sin(v * 19.0)
                r += grain + mott + .04
                g += grain * .55 + mott * .35
                b += grain * .25
                if rng.random() < .04:
                    r -= .10; g -= .07; b -= .04
            elif rough_pattern == "brick":
                grain = n * .07
                mortar = (x % 48 < 3) or (y % 24 < 2)
                if mortar:
                    r, g, b = (.42 + grain, .40 + grain, .36 + grain)
                else:
                    r += grain; g += grain * .72; b += grain * .5
            elif rough_pattern == "wood":
                grain = .045 * math.sin((u * 44.0) + 1.8 * math.sin(v * 8.0)) + n * .025
                r += grain; g += grain * .82; b += grain * .55
            elif rough_pattern == "plastic":
                grain = n * .025 + .008 * math.sin(u * 19 + v * 11)
                r += grain; g += grain; b += grain
            elif rough_pattern == "soot":
                grain = n * .045
                blot = .07 * (0.5 + 0.5 * math.sin(u * 21.0 + math.sin(v * 14.0)))
                r += grain - blot; g += grain - blot; b += grain - blot
            else:
                grain = n * .045
                r += grain; g += grain; b += grain
            px.extend((clamp(r), clamp(g), clamp(b), 1.0))
    img.pixels = px
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    return path


def edm_mat(name, color, rough=.8, metal=0.0, pattern="generic", size=256):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    group = createEdmNodeGroup("EDM_Default_Material", m)
    group.post_init(MAT_DESCS["EDM_Default_Material"])
    group.name = "Group"
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(_tex(name, color, pattern, size)), check_existing=True)
    m.node_tree.links.new(tex.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])

    rmo_path = TEXDIR / (name + "_RoughMet.png")
    if not rmo_path.exists():
        img = bpy.data.images.new(name + "_RoughMet", width=8, height=8, alpha=True)
        img.pixels = [1.0, rough, metal, 1.0] * 64
        img.filepath_raw = str(rmo_path)
        img.file_format = "PNG"
        img.save()
    rmo = m.node_tree.nodes.new("ShaderNodeTexImage")
    rmo.image = bpy.data.images.load(str(rmo_path), check_existing=True)
    rmo.image.colorspace_settings.name = "Non-Color"
    m.node_tree.links.new(rmo.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    return m


def mats():
    if MATS:
        return MATS
    MATS.update({
        "concrete": edm_mat("TPG_RUB01_Concrete", (.49, .48, .45), .94, .00, "concrete", 512),
        "concrete_dark": edm_mat("TPG_RUB01_ConcreteDark", (.32, .32, .30), .96, .00, "concrete", 512),
        "brick": edm_mat("TPG_RUB01_Brick", (.38, .22, .14), .93, .00, "brick", 256),
        "rust": edm_mat("TPG_RUB01_RustedSteel", (.34, .15, .065), .78, .55, "rust", 256),
        "steel": edm_mat("TPG_RUB01_Steel", (.20, .22, .22), .52, .74, "generic", 256),
        "galv": edm_mat("TPG_RUB01_Galvanized", (.46, .48, .48), .40, .78, "generic", 256),
        "rubber": edm_mat("TPG_RUB01_Rubber", (.025, .028, .027), .93, .00, "plastic", 256),
        "black_plastic": edm_mat("TPG_RUB01_BlackPlastic", (.025, .022, .020), .70, .00, "plastic", 256),
        "blue_plastic": edm_mat("TPG_RUB01_BluePlastic", (.025, .17, .35), .66, .00, "plastic", 256),
        "white_plastic": edm_mat("TPG_RUB01_WhitePlastic", (.72, .70, .66), .74, .00, "plastic", 256),
        "wood": edm_mat("TPG_RUB01_Wood", (.30, .20, .12), .88, .00, "wood", 256),
        "cardboard": edm_mat("TPG_RUB01_Cardboard", (.38, .30, .19), .95, .00, "wood", 256),
        "soot": edm_mat("TPG_RUB01_Soot", (.022, .018, .015), .97, .01, "soot", 256),
    })
    return MATS


def add_uv_if_missing(obj):
    if obj.type != "MESH":
        return
    if not obj.data.uv_layers:
        uv = obj.data.uv_layers.new(name="UVMap")
        for poly in obj.data.polygons:
            for li in poly.loop_indices:
                co = obj.data.vertices[obj.data.loops[li].vertex_index].co
                uv.data[li].uv = (co.x * .37, co.y * .37)


def apply_mod(obj, name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=name)


def box(name, loc, scale, mat=None, bevel=.025, rot=(0, 0, 0), coll=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        mod = o.modifiers.new("edge_break", "BEVEL")
        mod.width = min(bevel, min(scale) * .22)
        mod.segments = 2 if LOD == 0 else 1
        apply_mod(o, mod.name)
    if mat:
        o.data.materials.append(mat)
    add_uv_if_missing(o)
    if coll:
        get_edm_props(o).SPECIAL_TYPE = "COLLISION_SHELL"
    return o


def cyl(name, loc, radius, depth, mat=None, verts=12, rot=(0, 0, 0), coll=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    add_uv_if_missing(o)
    if coll:
        get_edm_props(o).SPECIAL_TYPE = "COLLISION_SHELL"
    return o


def torus(name, loc, major, minor, mat, rot=(0, 0, 0), major_segments=24, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor,
        major_segments=major_segments, minor_segments=minor_segments,
        location=loc, rotation=rot
    )
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    add_uv_if_missing(o)
    return o


def irregular_chunk(name, loc, scale, mat, seed, rot=None, roughness=.16, bevel=.035, cuts=1):
    rng = random.Random(seed)
    if rot is None:
        rot = (rng.uniform(-.45, .45), rng.uniform(-.45, .45), rng.uniform(-math.pi, math.pi))
    o = box(name, loc, scale, mat, bevel=0.0, rot=rot)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    if cuts > 0:
        bpy.ops.mesh.subdivide(number_cuts=cuts)
    bpy.ops.object.mode_set(mode="OBJECT")
    sx, sy, sz = scale
    for v in o.data.vertices:
        # preserve a solid chunk while breaking the perfect box silhouette
        v.co.x += rng.uniform(-roughness, roughness) * sx
        v.co.y += rng.uniform(-roughness, roughness) * sy
        v.co.z += rng.uniform(-roughness * .7, roughness * .7) * sz
    if bevel > 0:
        mod = o.modifiers.new("fracture_edge", "BEVEL")
        mod.width = min(bevel, min(scale) * .16)
        mod.segments = 1
        apply_mod(o, mod.name)
    add_uv_if_missing(o)
    return o


def flat_shard(name, loc, sx, sy, thickness, mat, seed, rot=(0, 0, 0)):
    return irregular_chunk(name, loc, (sx, sy, thickness), mat, seed, rot=rot, roughness=.11, bevel=.012, cuts=1)


def curve_mesh(name, pts, mat, radius=.012, resolution=0):
    c = bpy.data.curves.new(name + "_curve", "CURVE")
    c.dimensions = "3D"
    c.bevel_depth = radius
    c.bevel_resolution = resolution
    spl = c.splines.new("BEZIER")
    spl.bezier_points.add(len(pts) - 1)
    for bp, p in zip(spl.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, c)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.object
    o.name = name
    add_uv_if_missing(o)
    return o


def tube(name, loc, radius, depth, wall, mat, inner_mat, rot=(0, 0, 0), seg=20):
    # True hollow tube with outer wall, inner wall and annular rims.
    z0, z1 = -depth / 2, depth / 2
    ro = radius
    ri = max(.01, radius - wall)
    verts = []
    for z in (z0, z1):
        for r in (ro, ri):
            for i in range(seg):
                a = 2 * math.pi * i / seg
                verts.append((r * math.cos(a), r * math.sin(a), z))
    faces = []
    # index ring: z side * 2*seg + r side * seg + i
    def idx(zi, ri_idx, i):
        return zi * 2 * seg + ri_idx * seg + (i % seg)
    for i in range(seg):
        n = i + 1
        faces.append((idx(0,0,i), idx(0,0,n), idx(1,0,n), idx(1,0,i)))
        faces.append((idx(0,1,n), idx(0,1,i), idx(1,1,i), idx(1,1,n)))
        faces.append((idx(0,0,i), idx(0,1,i), idx(0,1,n), idx(0,0,n)))
        faces.append((idx(1,0,n), idx(1,1,n), idx(1,1,i), idx(1,0,i)))
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            ang = (math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0
            vv = (co.z - z0) / max(.001, depth)
            uv.data[li].uv = (ang, vv)
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(mat)
    # inner material on inward-facing polygons
    o.data.materials.append(inner_mat)
    # outer first seg*? polygons created alternating; set inner faces to material 1
    for pi, poly in enumerate(mesh.polygons):
        if pi % 4 == 1:
            poly.material_index = 1
    return o


def corrugated_sheet(name, loc, size=(1.4, .8), mat=None, rot=(0,0,0), seed=0):
    sx, sy = size
    seg = 18 if LOD == 0 else 10
    verts = []
    faces = []
    for j, y in enumerate((-sy/2, sy/2)):
        for i in range(seg + 1):
            x = -sx/2 + sx * i / seg
            z = .022 * math.sin(i * math.pi * 1.6)
            verts.append((x, y, z))
    for i in range(seg):
        a=i; b=i+1; c=(seg+1)+i+1; d=(seg+1)+i
        faces.append((a,b,c,d))
    mesh = bpy.data.meshes.new(name+"_mesh")
    mesh.from_pydata(verts, [], faces); mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=((co.x+sx/2)/sx,(co.y+sy/2)/sy)
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o)
    o.location=loc; o.rotation_euler=rot
    if mat: o.data.materials.append(mat)
    mod=o.modifiers.new("sheet_thickness","SOLIDIFY"); mod.thickness=.014
    apply_mod(o,mod.name)
    return o


def cinder_block(name, loc, rotz, M, scale=1.0):
    # Real open-cell geometry: two hollow cores through the block.
    L=.44*scale; W=.22*scale; H=.20*scale
    rail=.045*scale; end=.055*scale; mid=.045*scale
    parts=[
        (0, W/2-rail/2, L, rail),
        (0,-W/2+rail/2, L, rail),
        (-L/2+end/2,0,end,W-2*rail),
        ( L/2-end/2,0,end,W-2*rail),
        (0,0,mid,W-2*rail),
    ]
    cs, sn = math.cos(rotz), math.sin(rotz)
    for i,(lx,ly,dx,dy) in enumerate(parts):
        x=loc[0]+lx*cs-ly*sn; y=loc[1]+lx*sn+ly*cs
        box(f"{name}_{i}",(x,y,loc[2]),(dx,dy,H),M["concrete_dark"],.014,rot=(0,0,rotz))


def pallet(name, loc, rotz, M, broken=False):
    cs,sn=math.cos(rotz),math.sin(rotz)
    def tx(lx,ly):
        return (loc[0]+lx*cs-ly*sn,loc[1]+lx*sn+ly*cs,loc[2])
    for i,ly in enumerate((-.32,0,.32)):
        p=tx(0,ly)
        box(f"{name}_deck_{i}",p,(1.05,.13,.055),M["wood"],.012,rot=(0,0,rotz))
    for i,lx in enumerate((-.38,.38)):
        p=tx(lx,0)
        box(f"{name}_runner_{i}",(p[0],p[1],p[2]-.055),(.12,.82,.07),M["wood"],.012,rot=(0,0,rotz))
    if broken:
        p=tx(.48,.31)
        flat_shard(name+"_broken", (p[0],p[1],p[2]+.04), .42,.11,.035,M["wood"],SEED+885,
                   rot=(.15,-.12,rotz+.65))


def add_rebar_burst(prefix, base, count, M, seed, height=(.45,1.2), spread=.22):
    rng=random.Random(seed)
    for i in range(count):
        x=base[0]+rng.uniform(-spread,spread)
        y=base[1]+rng.uniform(-spread,spread)
        z=base[2]
        h=rng.uniform(*height)
        leanx=rng.uniform(-.30,.30); leany=rng.uniform(-.30,.30)
        pts=[(x,y,z),(x+leanx*.35,y+leany*.35,z+h*.45),
             (x+leanx,y+leany,z+h)]
        curve_mesh(f"{prefix}_{i}",pts,M["rust"],radius=rng.uniform(.010,.017),resolution=0)


def add_wire_tangle(prefix, center, count, M, seed, radius=.45):
    rng=random.Random(seed)
    for i in range(count):
        pts=[]
        x=center[0]+rng.uniform(-radius,radius)
        y=center[1]+rng.uniform(-radius,radius)
        z=center[2]+rng.uniform(-.08,.16)
        pts.append((x,y,z))
        for k in range(3):
            x += rng.uniform(-.28,.28)
            y += rng.uniform(-.28,.28)
            z += rng.uniform(-.10,.18)
            pts.append((x,y,z))
        curve_mesh(f"{prefix}_{i}",pts,M["rust" if i%3 else "steel"],radius=.006 if LOD==0 else .008,resolution=0)


def scatter_rubble(M):
    # Footprint target ~6.1 m x 6.1 m (20 x 20 ft), broad low mound like the reference image.
    # No base mesh is added.
    if LOD == 0:
        counts=(96,22,15)
    elif LOD == 1:
        counts=(48,9,7)
    else:
        counts=(18,2,4)

    # buried/interlocking central masses prevent visual holes while remaining genuine rubble geometry
    core_n = 9 if LOD == 0 else (6 if LOD == 1 else 4)
    for i in range(core_n):
        a=2*math.pi*i/core_n + .21
        r=1.15 + .35*math.sin(i*1.7)
        loc=(math.cos(a)*r,math.sin(a)*r, .18 + .11*math.sin(i))
        sc=(1.3+RNG.random()*.8, .85+RNG.random()*.65, .42+RNG.random()*.34)
        irregular_chunk(f"core_{i}",loc,sc,M["concrete_dark"],SEED+10+i,roughness=.13,bevel=.045,cuts=1)

    # small/medium concrete fragments
    for i in range(counts[0]):
        for _ in range(30):
            x=RNG.uniform(-3.05,3.05); y=RNG.uniform(-2.95,2.95)
            rn=(x/3.05)**2+(y/2.95)**2
            if rn <= 1.0:
                break
        h=max(0.0,1.0-rn)
        z=-.055 + 1.18*(h**1.35) + RNG.uniform(-.08,.18)
        sx=RNG.uniform(.18,.62)*(1.0+.18*h)
        sy=RNG.uniform(.16,.55)*(1.0+.12*h)
        sz=RNG.uniform(.10,.33)
        mat=M["concrete"] if i%4 else M["concrete_dark"]
        irregular_chunk(f"concrete_{i}",(x,y,z),(sx,sy,sz),mat,SEED+1000+i,
                        roughness=.18 if LOD==0 else .12,bevel=.025,cuts=1 if LOD<2 else 0)

    # brick/masonry fragments add the warmer warzone color notes seen in the references
    for i in range(counts[1]):
        for _ in range(20):
            x=RNG.uniform(-2.8,2.8); y=RNG.uniform(-2.7,2.7)
            rn=(x/2.8)**2+(y/2.7)**2
            if rn<1: break
        z=.05 + .82*max(0,1-rn) + RNG.uniform(-.06,.12)
        sc=(RNG.uniform(.18,.34),RNG.uniform(.09,.18),RNG.uniform(.07,.14))
        irregular_chunk(f"brick_{i}",(x,y,z),sc,M["brick"],SEED+2000+i,roughness=.10,bevel=.010,cuts=0)

    # larger broken slabs / beams produce the recognizable angular silhouette
    slab_specs=[
        ((-2.15,-.55,.58),(1.25,.72,.18),(.10,-.25,-.62)),
        (( 1.92,-.18,.78),(1.52,.54,.18),(-.12,.22,.36)),
        (( 2.12, .88,.95),(1.78,.42,.20),(.20,-.42,.82)),
        ((-1.12,1.48,.96),(1.30,.48,.17),(-.24,.16,-.30)),
        (( .15,-1.62,.58),(1.14,.58,.16),(.05,.30,.18)),
        ((-2.42,1.18,.42),(.90,.55,.16),(.24,-.18,1.00)),
        (( .65,.42,1.36),(1.05,.38,.15),(.30,.06,-.44)),
    ]
    for i,(loc,sc,rot) in enumerate(slab_specs[:counts[2]]):
        irregular_chunk(f"slab_{i}",loc,sc,M["concrete"],SEED+3000+i,rot=rot,roughness=.10,bevel=.022,cuts=1)

    # specific reference-driven debris vocabulary
    if LOD <= 1:
        cinder_block("cinder_front_left",(-1.05,-2.05,.25),-.28,M,1.0)
        cinder_block("cinder_center",( .52,-.62,.90), .43,M,.95)
        cinder_block("cinder_right",( 1.70,-1.18,.53),-.72,M,.82)
        if LOD == 0:
            cinder_block("cinder_back",(-.35,1.68,1.02),1.05,M,.88)
            cinder_block("cinder_side",(2.30,.22,.47),.18,M,.78)

        # broken concrete sewer/utility pipe at front center, plus steel pipes around pile
        tube("concrete_pipe_front",(.42,-2.08,.36),.31,1.20,.075,M["concrete_dark"],M["soot"],
             rot=(0,math.radians(74),math.radians(8)),seg=22 if LOD==0 else 14)
        tube("steel_pipe_left",(-2.28,-1.35,.35),.105,1.30,.026,M["steel"],M["soot"],
             rot=(0,math.radians(78),math.radians(-35)),seg=18 if LOD==0 else 12)
        tube("steel_pipe_mid",(1.10,.05,1.06),.085,.96,.022,M["rust"],M["soot"],
             rot=(0,math.radians(69),math.radians(53)),seg=16 if LOD==0 else 12)
        tube("steel_pipe_right",(2.15,-1.72,.30),.14,.82,.032,M["rust"],M["soot"],
             rot=(0,math.radians(82),math.radians(-68)),seg=18 if LOD==0 else 12)

        # rusted circular rim and small buried rubber tire as recognizable foreground clutter
        torus("rusted_rim",(2.33,-2.10,.34),.31,.045,M["rust"],rot=(math.radians(78),.20,.48),
              major_segments=24 if LOD==0 else 14,minor_segments=6)
        torus("buried_tire",(-2.58,-1.76,.28),.28,.095,M["rubber"],rot=(math.radians(83),-.18,-.72),
              major_segments=24 if LOD==0 else 14,minor_segments=8)

    if LOD == 0:
        # corrugated/bent metal, pallet and long structural scraps
        corrugated_sheet("corrugated_right",(1.80,1.48,1.02),(1.55,.78),M["galv"],rot=(.22,-.18,.74))
        corrugated_sheet("corrugated_left",(-1.75,.70,.80),(1.12,.62),M["rust"],rot=(-.18,.23,-.92))
        pallet("broken_pallet",(.05,.18,1.00),-.42,M,broken=True)

        box("beam_long_right",(2.08,.62,1.11),(1.72,.12,.12),M["rust"],.018,rot=(.10,.28,.84))
        box("beam_left",(-1.96,.38,.76),(1.30,.13,.13),M["steel"],.018,rot=(-.18,.08,-.60))
        box("pipe_support_bar",(.82,1.52,1.28),(1.38,.09,.09),M["rust"],.015,rot=(.24,-.25,.20))

        # exposed reinforcing steel: vertical bursts and tangled wires, concentrated where slabs broke
        add_rebar_burst("rebar_back",(-.15,1.47,1.14),9,M,SEED+4001,height=(.45,1.15),spread=.48)
        add_rebar_burst("rebar_right",(1.78,.82,1.12),7,M,SEED+4002,height=(.35,.95),spread=.38)
        add_rebar_burst("rebar_left",(-1.86,-.52,.64),6,M,SEED+4003,height=(.28,.80),spread=.30)
        add_wire_tangle("wire_center",(.15,.18,1.03),11,M,SEED+4200,.62)
        add_wire_tangle("wire_front",(-.22,-1.33,.47),8,M,SEED+4300,.52)
        add_wire_tangle("wire_right",(1.72,.30,.90),7,M,SEED+4400,.48)

        # protruding rebar from slab faces
        for j in range(5):
            x=-2.48+j*.10
            curve_mesh(f"slab_rebar_{j}",[(x,-.64,.52),(x-.12,-.80,.60),(x-.26,-.90,.72)],
                       M["rust"],radius=.013)

        # trash / civilian construction waste seen in the generated target
        irregular_chunk("trash_black_bag",(1.10,-2.22,.22),(.52,.34,.20),M["black_plastic"],SEED+5001,
                        roughness=.26,bevel=.045,cuts=2)
        flat_shard("trash_blue_sheet",(-1.44,-2.34,.16),.46,.28,.018,M["blue_plastic"],SEED+5002,
                   rot=(.02,.03,-.32))
        irregular_chunk("trash_white_bag",(-1.85,-1.85,.24),(.44,.28,.18),M["white_plastic"],SEED+5003,
                        roughness=.30,bevel=.05,cuts=2)
        flat_shard("cardboard_flat",(-.55,-2.35,.12),.62,.38,.022,M["cardboard"],SEED+5004,
                   rot=(.04,-.02,.18))
        irregular_chunk("cardboard_crush",(2.02,-1.10,.50),(.48,.31,.22),M["cardboard"],SEED+5005,
                        roughness=.22,bevel=.025,cuts=1)
        flat_shard("white_scrap",(2.45,-.80,.35),.32,.25,.018,M["white_plastic"],SEED+5006,
                   rot=(.16,-.10,.72))

    elif LOD == 1:
        add_rebar_burst("rebar_lod1",(.20,.92,1.05),7,M,SEED+4600,height=(.35,.92),spread=.60)
        pallet("pallet_lod1",(.05,.18,.92),-.42,M,broken=False)
        box("beam_lod1",(1.90,.72,1.03),(1.65,.13,.13),M["rust"],.018,rot=(.12,.24,.82))
        irregular_chunk("trash_lod1",(1.10,-2.16,.22),(.48,.32,.19),M["black_plastic"],SEED+5600,
                        roughness=.22,bevel=.04,cuts=1)

    else:
        # LOD2 retains only strongest silhouette elements.
        box("beam_lod2",(1.70,.75,.98),(1.65,.14,.14),M["rust"],.014,rot=(.10,.20,.80))
        cyl("pipe_lod2",(.45,-1.90,.32),.28,1.05,M["concrete_dark"],10,
            rot=(0,math.radians(74),math.radians(8)))


def destroyed_pass(M):
    if not DESTROYED:
        return
    # A rubble pile is already destroyed material; its DCS destruction state becomes
    # more dispersed and fire-blackened rather than an implausible second collapse.
    for i in range(12 if LOD==0 else 6):
        a=RNG.uniform(0,2*math.pi); r=RNG.uniform(.35,2.65)
        x=math.cos(a)*r; y=math.sin(a)*r
        z=.10 + .75*(1-r/3.0) + RNG.uniform(-.10,.12)
        irregular_chunk(f"burned_{i}",(x,y,z),(RNG.uniform(.22,.58),RNG.uniform(.18,.46),RNG.uniform(.10,.26)),
                        M["soot"],SEED+7000+i,roughness=.22,bevel=.02,cuts=1 if LOD==0 else 0)
    if LOD==0:
        add_wire_tangle("burnt_wires",(.65,.55,.82),8,M,SEED+7100,.56)
        irregular_chunk("burnt_plastic",(1.12,-2.12,.18),(.56,.36,.16),M["soot"],SEED+7200,
                        roughness=.28,bevel=.04,cuts=2)


def add_collision():
    # Coarse collision only for meaningful pile mass, separate from visual batching.
    # It intentionally stops short of individual rebar/pipes/trash.
    box("COLL_Rubble_Base",(0,0,.27),(5.45,5.05,.58),None,0,coll=True)
    box("COLL_Rubble_Mid",(0,.10,.72),(4.20,3.75,.70),None,0,coll=True)
    box("COLL_Rubble_Core",(.05,.28,1.16),(2.75,2.55,.72),None,0,coll=True)


def batch_visuals():
    # Preserve collision nodes; batch disconnected static meshes by material to keep
    # the high visible detail without exporting hundreds of independent scene nodes.
    groups={}
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or o.name.startswith("COLL_"):
            continue
        if len(o.data.materials) != 1:
            continue
        key=o.data.materials[0].name if o.data.materials[0] else "None"
        groups.setdefault(key,[]).append(o)
    for key,objs in groups.items():
        if len(objs)<2:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active=objs[0]
        bpy.ops.object.join()
        objs[0].name="BATCH_"+key


def validate_scene():
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    if not meshes:
        raise RuntimeError("Rubble scene has no mesh objects.")
    for o in meshes:
        if o.name.startswith("COLL_"):
            continue
        if not o.data.uv_layers:
            raise RuntimeError(f"Missing UV layer: {o.name}")
    # footprint/height sanity for the intended 20 x 20 ft class asset
    pts=[]
    for o in meshes:
        if o.name.startswith("COLL_"):
            continue
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    minx=min(p.x for p in pts); maxx=max(p.x for p in pts)
    miny=min(p.y for p in pts); maxy=max(p.y for p in pts)
    minz=min(p.z for p in pts); maxz=max(p.z for p in pts)
    print(f"[TPG RUBBLE] variant={VARIANT} meshes={len(meshes)} bounds=({maxx-minx:.2f}m x {maxy-miny:.2f}m x {maxz-minz:.2f}m)")
    if maxx-minx < 5.0 or maxy-miny < 5.0:
        raise RuntimeError("Rubble footprint unexpectedly small.")
    if maxz < 1.0:
        raise RuntimeError("Rubble mound unexpectedly low.")


def main():
    bpy.context.scene.unit_settings.system="METRIC"
    M=mats()
    scatter_rubble(M)
    destroyed_pass(M)
    if LOD == 0:
        add_collision()
    batch_visuals()
    validate_scene()


main()
