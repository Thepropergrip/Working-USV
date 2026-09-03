import bpy, math, os, random, zlib
from pathlib import Path

WORK = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
TEXDIR = WORK / "edm-artifacts" / "Textures"
TEXDIR.mkdir(parents=True, exist_ok=True)

from materials.materials import build_material_descriptions
from materials.material_tools import createEdmNodeGroup
from enums import NodeSocketInDefaultEnum
from objects_custom_props import get_edm_props

MAT_DESCS = build_material_descriptions()
M = {}

LOD = int(os.environ.get("TPG_TACOMA_LOD", "0"))
DESTROYED = os.environ.get("TPG_TACOMA_DESTROYED", "0") == "1"

# 2016 Tacoma DCLB / photographed truck reference dimensions, metres.
LENGTH = 5.728
WIDTH = 1.895
WHEELBASE = 3.571
WHEEL_R = 0.405
TIRE_W = 0.285
FRONT_AXLE = WHEELBASE / 2.0
REAR_AXLE = -WHEELBASE / 2.0

def _tex(name, base, rough=.7, metal=0.0, size=256, dirt=0.0):
    path = TEXDIR / (name + ".png")
    if path.exists():
        return path
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    rng = random.Random(zlib.crc32(name.encode("utf-8")) & 0xffffffff)
    px = []
    for y in range(size):
        v = y / max(1, size - 1)
        for x in range(size):
            n = (rng.random() - .5) * .035
            d = 0.0
            if dirt:
                # Fine dry-road speckle and subtle lower-value dirt variation.
                d += dirt * max(0.0, (rng.random() - .82)) * 1.7
                d += dirt * .16 * (math.sin(x*.083 + y*.037) + 1.0) * .5
            px.extend((
                max(0.0, min(1.0, base[0] + n - d)),
                max(0.0, min(1.0, base[1] + n - d*.82)),
                max(0.0, min(1.0, base[2] + n - d*.58)),
                1.0))
    img.pixels = px
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()

    rpath = TEXDIR / (name + "_RoughMet.png")
    if not rpath.exists():
        r = bpy.data.images.new(name+"_RoughMet", width=8, height=8, alpha=True)
        r.pixels = [1.0, rough, metal, 1.0] * 64
        r.filepath_raw = str(rpath)
        r.file_format = "PNG"
        r.save()
    return path

def mat(name, color, rough=.7, metal=0.0, dirt=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    group = createEdmNodeGroup("EDM_Default_Material", m)
    group.post_init(MAT_DESCS["EDM_Default_Material"])
    group.name = "Group"
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(_tex(name, color, rough, metal, dirt=dirt)), check_existing=True)
    m.node_tree.links.new(tex.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])
    rmo = m.node_tree.nodes.new("ShaderNodeTexImage")
    rmo.image = bpy.data.images.load(str(TEXDIR/(name+"_RoughMet.png")), check_existing=True)
    rmo.image.colorspace_settings.name = "Non-Color"
    m.node_tree.links.new(rmo.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    return m

def materials():
    if M:
        return M
    M.update({
        "paint": mat("TPG_TACOMA_Quicksand_4T8", (.59,.53,.42), .46, .05, .07),
        "paint_clean": mat("TPG_TACOMA_QuicksandClean", (.61,.55,.44), .42, .05, .018),
        "black_plastic": mat("TPG_TACOMA_BlackPlastic", (.028,.030,.030), .84, .02, .025),
        "black_metal": mat("TPG_TACOMA_BlackMetal", (.020,.022,.023), .48, .72, .018),
        "rubber": mat("TPG_TACOMA_TireRubber", (.018,.019,.019), .94, .01, .035),
        "rim": mat("TPG_TACOMA_TRDWheelDark", (.12,.13,.14), .32, .78, .01),
        "rim_face": mat("TPG_TACOMA_TRDWheelMachined", (.48,.49,.48), .25, .88, .008),
        "glass": mat("TPG_TACOMA_TintedGlass", (.018,.034,.040), .16, .08, .005),
        "chrome": mat("TPG_TACOMA_Chrome", (.64,.66,.67), .18, .93, .004),
        "headlamp": mat("TPG_TACOMA_HeadlampLens", (.70,.76,.77), .12, .08, .003),
        "amber": mat("TPG_TACOMA_AmberLens", (.83,.30,.025), .22, .04, .004),
        "red": mat("TPG_TACOMA_RedLens", (.56,.020,.018), .22, .03, .004),
        "white": mat("TPG_TACOMA_ReflectiveWhite", (.78,.80,.78), .34, .03, .004),
        "blue": mat("TPG_TACOMA_PlateBlue", (.028,.11,.30), .46, .03, .004),
        "mud": mat("TPG_TACOMA_DriedRoadMud", (.31,.25,.17), .96, .01, .16),
        "steel": mat("TPG_TACOMA_Steel", (.16,.17,.18), .50, .78, .025),
        "burnt": mat("TPG_TACOMA_Burnt", (.055,.040,.030), .88, .18, .11),
        "soot": mat("TPG_TACOMA_Soot", (.012,.010,.009), .98, .01, .12),
    })
    return M

def box(name, loc, scale, material, bevel=.03, rot=(0,0,0), coll=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        mod = o.modifiers.new("edge_soften", "BEVEL")
        mod.width = bevel
        mod.segments = 2 if LOD < 2 else 1
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if material:
        o.data.materials.append(material)
    if coll:
        get_edm_props(o).SPECIAL_TYPE = "COLLISION_SHELL"
    return o

def cyl(name, loc, radius, depth, material, verts=24, rot=(0,0,0), parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if material:
        o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o

def torus(name, loc, major, minor, material, rot=(0,0,0), parent=None, major_segments=32, minor_segments=10):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
        major_segments=major_segments, minor_segments=minor_segments,
        location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if material:
        o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o

def sphere(name, loc, radius, material, parent=None, seg=20, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=radius, location=loc)
    o = bpy.context.object
    o.name = name
    if material:
        o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o

def tube(name, pts, radius, material, bevel_res=2):
    c = bpy.data.curves.new(name+"_curve","CURVE")
    c.dimensions = "3D"
    c.bevel_depth = radius
    c.bevel_resolution = bevel_res
    s = c.splines.new("POLY")
    s.points.add(len(pts)-1)
    for p, co in zip(s.points, pts):
        p.co = (co[0],co[1],co[2],1.0)
    o = bpy.data.objects.new(name,c)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.object

def text_obj(text, name, loc, size, material, rot=(math.radians(90),0,0), align="CENTER"):
    c = bpy.data.curves.new(name+"_curve","FONT")
    c.body = text
    c.align_x = align
    c.align_y = "CENTER"
    c.size = size
    c.extrude = 0.0
    c.bevel_depth = 0.0
    o = bpy.data.objects.new(name,c)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(material)
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.object

def action_rot(obj, arg, axis, neg_angle, pos_angle):
    obj.rotation_mode = "XYZ"
    act = bpy.data.actions.new(f"{arg} {obj.name}")
    obj.animation_data_create()
    obj.animation_data.action = act
    for frame, ang in ((0,neg_angle),(100,0.0),(200,pos_angle)):
        vals = [0.0,0.0,0.0]
        vals[axis] = ang
        obj.rotation_euler = vals
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    obj.rotation_euler = (0.0,0.0,0.0)

def parent_keep(child, parent):
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw

def arch_flare(name, wheel_x, side_y, zc, material):
    pts=[]
    # Upper wheel-arch flare, photo-like black plastic lip.
    for i in range(25 if LOD==0 else 13):
        a = math.radians(12 + (156.0*i/((24 if LOD==0 else 12))))
        x = wheel_x + .49*math.cos(a)
        z = zc + .49*math.sin(a)
        pts.append((x, side_y, z))
    return tube(name, pts, .055 if LOD==0 else .065, material, 2 if LOD==0 else 1)

def wheel(prefix, x, side):
    y = side*(WIDTH/2 + .005)
    z = WHEEL_R
    steer = bpy.data.objects.new(prefix+"_STEER", None)
    steer.location = (x,y,z)
    bpy.context.collection.objects.link(steer)
    roll = bpy.data.objects.new(prefix+"_ROLL", None)
    roll.location = (x,y,z)
    bpy.context.collection.objects.link(roll)
    if "FRONT" in prefix:
        roll.parent = steer
        # Preserve world location after parenting.
        roll.matrix_parent_inverse = steer.matrix_world.inverted()
        action_rot(steer, 9, 2, math.radians(-31), math.radians(31))
    action_rot(roll, 8, 1, -2*math.pi, 2*math.pi)

    tire = cyl(prefix+"_TIRE", (x,y,z), WHEEL_R, TIRE_W, M["rubber"],
               48 if LOD==0 else 24, rot=(math.radians(90),0,0))
    parent_keep(tire, roll)
    # A shallow torus gives the sidewall/tread shoulder a believable rounded profile.
    if LOD < 2:
        shoulder = torus(prefix+"_SHOULDER", (x,y,z), .325, .080, M["rubber"],
                         rot=(math.radians(90),0,0), major_segments=36 if LOD==0 else 20,
                         minor_segments=12 if LOD==0 else 6)
        parent_keep(shoulder, roll)

    rim = cyl(prefix+"_RIM", (x,y-side*.012,z), .205, .292, M["rim"],
              36 if LOD==0 else 20, rot=(math.radians(90),0,0))
    parent_keep(rim, roll)
    hub = cyl(prefix+"_HUB", (x,y-side*.156,z), .072, .018, M["black_metal"], 24,
              rot=(math.radians(90),0,0))
    parent_keep(hub, roll)

    if LOD==0:
        # Six split/machined spoke groups approximating the photographed 16-in TRD Off Road alloy.
        for i in range(6):
            a = i*math.pi/3
            for off in (-.045,.045):
                rr=.118
                sx=x+rr*math.cos(a)+off*math.sin(a)
                sz=z+rr*math.sin(a)-off*math.cos(a)
                sp=box(f"{prefix}_SPOKE_{i}_{off:+.3f}",(sx,y-side*.166,sz),
                       (.155,.018,.044),M["rim_face"],.012,rot=(0,-a,0))
                parent_keep(sp,roll)
        for i in range(24):
            a=2*math.pi*i/24
            tx=x+.392*math.cos(a); tz=z+.392*math.sin(a)
            lug=box(f"{prefix}_TREAD_{i}",(tx,y,tz),(.085,.300,.040),M["rubber"],.008,rot=(0,-a,0))
            parent_keep(lug,roll)
        for i in range(6):
            a=2*math.pi*i/6
            lx=x+.053*math.cos(a); lz=z+.053*math.sin(a)
            nut=cyl(f"{prefix}_LUGNUT_{i}",(lx,y-side*.170,lz),.012,.020,M["steel"],10,
                    rot=(math.radians(90),0,0))
            parent_keep(nut,roll)
    return steer, roll

def add_front():
    # bumper / lower valance
    box("FRONT_BUMPER_QUICKSAND",(2.72,0,.66),(.30,1.86,.34),M["paint"],.08)
    box("FRONT_LOWER_BLACK",(2.875,0,.48),(.12,1.58,.24),M["black_plastic"],.06)
    # grille bezel and dark insert
    box("GRILLE_BEZEL",(2.86,0,1.03),(.075,1.36,.52),M["black_plastic"],.11)
    box("GRILLE_INNER",(2.902,0,1.03),(.035,1.17,.38),M["black_metal"],.05)
    if LOD<2:
        # characteristic two horizontal bars and rectangular slot field
        for z in (.94,1.12):
            box(f"GRILLE_BAR_{z}",(2.928,0,z),(.028,1.14,.055),M["black_plastic"],.016)
        if LOD==0:
            for row,z in enumerate((.88,1.01,1.15,1.28)):
                for col in range(11):
                    yy=-.52+col*.104
                    box(f"GRILLE_SLOT_{row}_{col}",(2.947,yy,z),(.012,.056,.044),M["black_plastic"],.010)
        # Toyota emblem stylized as the recognizable three-oval mark.
        torus("TOYOTA_OUTER",(2.958,0,1.05),.125,.020,M["rim_face"],rot=(0,math.radians(90),0),major_segments=32,minor_segments=8)
        torus("TOYOTA_INNER_V",(2.968,0,1.05),.070,.013,M["rim_face"],rot=(0,math.radians(90),0),major_segments=24,minor_segments=6)

    # headlights and fog lights
    for side in (-1,1):
        y=side*.72
        box(f"HEADLAMP_{side}",(2.79,y,1.25),(.12,.39,.22),M["headlamp"],.065)
        if LOD<2:
            sphere(f"PROJECTOR_{side}",(2.854,y-side*.05,1.27),.083,M["chrome"],seg=24,rings=12)
            sphere(f"PROJECTOR_GLASS_{side}",(2.897,y-side*.05,1.27),.059,M["headlamp"],seg=20,rings=10)
            box(f"TURN_AMBER_{side}",(2.846,y+side*.145,1.25),(.04,.080,.115),M["amber"],.025)
            box(f"DRL_STRIP_{side}",(2.865,y-side*.025,1.16),(.025,.25,.025),M["white"],.010)
        cyl(f"FOG_{side}",(2.882,side*.65,.73),.092,.055,M["headlamp"],24,rot=(0,math.radians(90),0))
        cyl(f"FOG_RING_{side}",(2.901,side*.65,.73),.115,.034,M["black_plastic"],24,rot=(0,math.radians(90),0))

def add_body():
    paint=M["burnt"] if DESTROYED else M["paint"]
    # underbody/frame
    box("FRAME_L",(0,.53,.43),(4.75,.10,.12),M["steel"],.02)
    box("FRAME_R",(0,-.53,.43),(4.75,.10,.12),M["steel"],.02)
    box("SKID_PLATE",(1.42,0,.34),(1.05,.84,.07),M["steel"],.03)
    for ax in (FRONT_AXLE,REAR_AXLE):
        cyl(f"AXLE_{ax:+.2f}",(ax,0,.44),.060,1.54,M["steel"],16,rot=(math.radians(90),0,0))
        sphere(f"DIFF_{ax:+.2f}",(ax,0,.44),.16,M["steel"],seg=16,rings=8)

    # hood and front fenders
    box("HOOD",(1.91,0,1.27),(1.45,1.64,.18),paint,.07,rot=(0,math.radians(-2.5),0))
    box("FRONT_FENDER_L",(1.58,.79,1.04),(1.32,.18,.52),paint,.08)
    box("FRONT_FENDER_R",(1.58,-.79,1.04),(1.32,.18,.52),paint,.08)

    # rocker / lower body structure
    box("CAB_ROCKER",(0.18,0,.76),(2.32,1.68,.34),paint,.08)
    # doors as distinct surface panels so seams read at close range
    for side in (-1,1):
        sy=side*.855
        for name,x,w in (("FRONT_DOOR",.55,1.03),("REAR_DOOR",-.47,.94)):
            box(f"{name}_{side}",(x,sy,.98),(w,.055,.72),paint,.035)
        # panel seams
        if LOD<2:
            for x in (.02,1.08,-.96):
                box(f"DOOR_SEAM_{side}_{x}",(x,sy+side*.030,1.00),(.015,.008,.72),M["black_plastic"],.0)
        # handles
        for x in (.55,-.47):
            box(f"DOOR_HANDLE_{side}_{x}",(x+.11,sy+side*.045,1.18),(.19,.035,.045),paint,.018)

    # upper cab shell, roof, pillars
    box("CAB_ROOF",(0.05,0,1.68),(2.17,1.66,.13),paint,.07)
    for side in (-1,1):
        y=side*.82
        box(f"A_PILLAR_{side}",(.98,y,1.46),(.18,.10,.55),M["black_plastic"],.035,rot=(0,math.radians(-13),0))
        box(f"B_PILLAR_{side}",(.09,y,1.45),(.11,.10,.56),M["black_plastic"],.025)
        box(f"C_PILLAR_{side}",(-.88,y,1.43),(.12,.10,.54),paint,.030)
        # front & rear tinted side windows
        box(f"FRONT_WINDOW_{side}",(.55,y+side*.011,1.47),(.70,.025,.42),M["glass"],.065)
        box(f"REAR_WINDOW_{side}",(-.43,y+side*.011,1.47),(.70,.025,.42),M["glass"],.060)

    # windshield and rear cab glass
    box("WINDSHIELD",(1.03,0,1.49),(.055,1.43,.49),M["glass"],.065,rot=(0,math.radians(-13),0))
    box("CAB_REAR_GLASS",(-1.00,0,1.45),(.035,1.38,.44),M["glass"],.045)

    # bed lower & shoulders, leaving wheel region visually open
    box("BED_FLOOR",(-1.84,0,.75),(1.70,1.62,.15),paint,.04)
    box("BED_SIDE_L",(-1.86,.82,1.02),(1.70,.12,.48),paint,.06)
    box("BED_SIDE_R",(-1.86,-.82,1.02),(1.70,.12,.48),paint,.06)
    box("TAILGATE",(-2.70,0,1.02),(.12,1.65,.48),paint,.05)

    # camper shell exactly as photographed/concept: paint matched, large dark side glass.
    box("CAMPER_SHELL",(-1.83,0,1.45),(1.62,1.66,.76),paint,.08)
    box("CAMPER_ROOF",(-1.83,0,1.82),(1.70,1.68,.11),paint,.055)
    for side in (-1,1):
        box(f"CAMPER_WINDOW_{side}",(-1.83,side*.835,1.54),(1.23,.030,.43),M["glass"],.055)
    box("CAMPER_REAR_GLASS",(-2.665,0,1.55),(.035,1.42,.46),M["glass"],.05)

    # mirrors
    for side in (-1,1):
        y=side*.99
        box(f"MIRROR_BASE_{side}",(.94,y,1.48),(.18,.18,.17),M["black_plastic"],.04)
        box(f"MIRROR_CAP_{side}",(.90,y+side*.09,1.51),(.27,.18,.18),paint,.065)
        box(f"MIRROR_GLASS_{side}",(.865,y+side*.185,1.51),(.19,.012,.12),M["glass"],.03)

    # black tube rock sliders, with support stubs.
    for side in (-1,1):
        y=side*1.01
        tube(f"ROCK_SLIDER_{side}",[(-1.05,y,.60),(1.12,y,.60)],.045,M["black_metal"],2 if LOD==0 else 1)
        if LOD==0:
            for x in (-.72,0,.72):
                tube(f"ROCK_SLIDER_BRACE_{side}_{x}",[(x,side*.80,.55),(x,y,.60)],.028,M["black_metal"],1)

    # Black plastic wheel arch flares matching the photos.
    for side in (-1,1):
        arch_flare(f"FRONT_FLARE_{side}",FRONT_AXLE,side*.895,.49,M["black_plastic"])
        arch_flare(f"REAR_FLARE_{side}",REAR_AXLE,side*.895,.49,M["black_plastic"])

    # modest photographed ride height: no invented lift.
    wheel("FRONT_L" if 1 else "", FRONT_AXLE, 1)
    wheel("FRONT_R", FRONT_AXLE, -1)
    wheel("REAR_L", REAR_AXLE, 1)
    wheel("REAR_R", REAR_AXLE, -1)

def add_rack_and_lights():
    # Two low-profile rack/platform sections, black powder coat.
    for cx,l in ((.18,1.78),(-1.83,1.48)):
        for side in (-1,1):
            box(f"RACK_SIDE_{cx}_{side}",(cx,side*.76,1.88),(l,.055,.14),M["black_metal"],.025)
        for i in range(6 if LOD==0 else 3):
            x=cx-l*.42+i*(l*.84/max(1,(5 if LOD==0 else 2)))
            box(f"RACK_CROSS_{cx}_{i}",(x,0,1.90),(.045,1.52,.045),M["black_metal"],.012)
        if LOD==0:
            for side in (-1,1):
                for i in range(5):
                    x=cx-l*.40+i*(l*.80/4)
                    cyl(f"RACK_BOLT_{cx}_{side}_{i}",(x,side*.785,1.90),.012,.018,M["steel"],10)

    # Black Oak hood/cowl cube lights with rear cooling fins and four LED optics.
    if LOD<2:
        for side in (-1,1):
            x=1.17; y=side*.82; z=1.57
            box(f"DITCH_BRACKET_{side}",(x-.06,y,z-.11),(.15,.055,.17),M["black_metal"],.015)
            box(f"BLACK_OAK_HOUSING_{side}",(x,y+side*.025,z),(.16,.22,.18),M["black_metal"],.035)
            # front lens faces out slightly forward/side but retain square four-cell identity.
            face_y=y+side*.142
            for r in (-.038,.038):
                for c in (-.038,.038):
                    sphere(f"BLACK_OAK_LED_{side}_{r}_{c}",(x+r,face_y,z+c),.025,M["headlamp"],seg=16,rings=8)
            if LOD==0:
                for i in range(5):
                    box(f"BLACK_OAK_FIN_{side}_{i}",(x-.092+i*.046,y-side*.105,z),(.018,.045,.19),M["black_plastic"],.006)

def add_rear():
    paint=M["burnt"] if DESTROYED else M["paint"]
    # tail lamps
    for side in (-1,1):
        y=side*.77
        box(f"TAIL_LAMP_{side}",(-2.765,y,1.15),(.10,.22,.34),M["red"],.045)
        if LOD<2:
            box(f"TAIL_REVERSE_{side}",(-2.82,y,1.10),(.025,.16,.085),M["white"],.018)
    # heavy duty photographed/concept rear bumper
    box("REAR_HD_BUMPER",(-2.84,0,.63),(.28,1.88,.31),M["black_metal"],.045)
    box("REAR_BUMPER_CENTER",(-2.965,0,.68),(.05,.78,.20),M["black_metal"],.022)
    # bright amber auxiliary backup lights recessed in bumper
    for side in (-1,1):
        y=side*.55
        box(f"REAR_AMBER_BACKUP_{side}",(-2.995,y,.69),(.022,.20,.10),M["amber"],.018)
        if LOD==0:
            for rr in (-.030,.030):
                for cc in (-.055,.0,.055):
                    sphere(f"REAR_AMBER_LED_{side}_{rr}_{cc}",(-3.010,y+cc,.69+rr),.013,M["amber"],seg=12,rings=6)
    # recovery points / D-rings
    if LOD==0:
        for side in (-1,1):
            torus(f"D_RING_{side}",(-2.995,side*.33,.53),.072,.018,M["steel"],rot=(0,math.radians(90),0),major_segments=20,minor_segments=7)
    # hitch receiver
    box("HITCH_RECEIVER",(-3.02,0,.42),(.22,.13,.13),M["black_metal"],.018)
    # tailgate handle & Tacoma emboss
    box("TAILGATE_HANDLE",(-2.77,0,1.18),(.05,.27,.085),M["black_plastic"],.025)
    if LOD==0:
        text_obj("TACOMA","TAILGATE_TACOMA",(-2.772,0,1.00),.16,M["paint_clean"],rot=(0,math.radians(90),math.radians(90)))
        text_obj("V6","TAILGATE_V6",(-2.778,-.57,1.03),.09,M["black_plastic"],rot=(0,math.radians(90),math.radians(90)))

def add_badges_plate_weather():
    if LOD>0:
        return
    # Side badges / decals. Flat decals, no raised floating lettering.
    for side in (-1,1):
        y=side*.889
        text_obj("TACOMA",f"SIDE_TACOMA_{side}",(.53,y,1.02),.105,M["black_plastic"],
                 rot=(math.radians(90),0,0 if side>0 else math.pi))
        text_obj("TRD 4X4",f"TRD_DECAL_{side}",(-2.05,y,1.32),.115,M["black_plastic"],
                 rot=(math.radians(90),0,0 if side>0 else math.pi))
        text_obj("OFF ROAD",f"TRD_SUB_{side}",(-2.03,y,1.22),.055,M["red"],
                 rot=(math.radians(90),0,0 if side>0 else math.pi))

    # Fictional DCS plate, realistic proportions/reflection rather than a cartoon logo.
    box("DCS_PLATE_FRONT",(2.953,0,.55),(.018,.305,.155),M["white"],.012)
    text_obj("DCS 416", "DCS_PLATE_FRONT_TEXT", (2.965,0,.553), .072, M["blue"],
             rot=(0,math.radians(90),math.radians(90)))
    box("DCS_PLATE_REAR",(-3.003,0,.75),(.018,.305,.155),M["white"],.012)
    text_obj("DCS 416", "DCS_PLATE_REAR_TEXT", (-3.015,0,.753), .072, M["blue"],
             rot=(0,math.radians(-90),math.radians(90)))

    # Thin dried-mud/road-wear patches concentrated exactly where visible in the photos:
    # lower doors, rocker and the trailing edge of the front flare.
    rng=random.Random(4162016)
    for side in (-1,1):
        sy=side*.892
        for i in range(22):
            x=rng.uniform(-.9,1.12); z=rng.uniform(.68,.88)
            w=rng.uniform(.025,.12); h=rng.uniform(.008,.035)
            box(f"MUD_SIDE_{side}_{i}",(x,sy+side*.006,z),(w,.004,h),M["mud"],.002)
        for i in range(12):
            a=math.radians(rng.uniform(55,135))
            x=FRONT_AXLE+.50*math.cos(a); z=.49+.50*math.sin(a)
            box(f"MUD_FLARE_{side}_{i}",(x,side*.902,z),(.035,.006,.018),M["mud"],.003,rot=(0,-a,0))

def add_interior():
    if LOD>0:
        return
    # Only what is visible through the dark tint: seats, dash silhouette, wheel.
    for x in (.45,-.45):
        for side in (-1,1):
            box(f"SEAT_{x}_{side}",(x,side*.36,1.11),(.38,.44,.52),M["black_plastic"],.08)
    box("DASH",(1.00,0,1.28),(.28,1.28,.20),M["black_plastic"],.05)
    torus("STEERING_WHEEL",(1.00,-.32,1.34),.15,.018,M["black_plastic"],
          rot=(0,math.radians(90),0),major_segments=24,minor_segments=7)

def add_collision():
    # Separate low-complexity collision-only volumes; no giant detailed render mesh is used as collision.
    box("COLLISION_MAIN",(0,0,1.03),(4.55,1.68,1.35),None,0,coll=True)
    box("COLLISION_NOSE",(2.31,0,.92),(1.12,1.70,.90),None,0,coll=True)
    box("COLLISION_REAR",(-2.37,0,1.06),(1.15,1.72,1.47),None,0,coll=True)

def wreck_damage():
    if not DESTROYED:
        return
    # Visible wreck-specific damage; this is not merely a darkened intact truck.
    box("CRUSHED_HOOD",(1.92,.06,1.20),(1.30,1.46,.10),M["soot"],.04,rot=(0,math.radians(7),math.radians(3)))
    box("BROKEN_CAMPER_PANEL",(-1.95,.45,1.50),(1.10,.05,.60),M["soot"],.025,rot=(math.radians(8),0,math.radians(-11)))
    tube("BENT_RACK",[(-2.40,.72,1.70),(-1.75,.65,1.55),(-1.10,.58,1.48)],.045,M["burnt"],1)
    # debris shards under rear quarter
    for i,(x,y,z) in enumerate(((-2.25,.90,.18),(-1.75,-.88,.16),(.85,.94,.15))):
        box(f"WRECK_DEBRIS_{i}",(x,y,z),(.35,.16,.06),M["burnt"],.01,rot=(0,math.radians(12*i),math.radians(18-9*i)))

def build():
    materials()
    add_body()
    add_front()
    add_rear()
    if LOD < 2 and not DESTROYED:
        add_rack_and_lights()
    elif LOD < 2 and DESTROYED:
        # some rack remains on destroyed model
        add_rack_and_lights()
    add_badges_plate_weather()
    add_interior()
    wreck_damage()
    add_collision()

    # Origin/ground check marker is intentionally absent from export.
    print(f"[TPG TACOMA] built LOD={LOD} destroyed={DESTROYED} objects={len(bpy.context.scene.objects)}")
    print("[TPG TACOMA] wheel animation arguments: 8 rotation, 9 steering")
    print("[TPG TACOMA] reference: 2016 Tacoma TRD Off Road 4x4 DCLB, Quicksand, photographed custom truck")

build()
