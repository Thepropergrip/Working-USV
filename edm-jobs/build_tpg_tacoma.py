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
        mod.segments = 5 if LOD == 0 else (3 if LOD == 1 else 1)
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(22)
        bpy.context.view_layer.objects.active = o
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except:
            pass
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
    s = c.splines.new("BEZIER")
    s.bezier_points.add(len(pts)-1)
    for bp, co in zip(s.bezier_points, pts):
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name,c)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.object
    o.select_set(False)
    return o

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
    act = bpy.data.actions.new(f"{arg}_{obj.name}")
    obj.animation_data_create()
    obj.animation_data.action = act
    for frame, ang in ((0,neg_angle),(100,0.0),(200,pos_angle)):
        vals = [0.0,0.0,0.0]
        vals[axis] = ang
        obj.rotation_euler = vals
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    bpy.context.scene.frame_set(100)

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


# ----------------------------- V2 geometry helpers -----------------------------
def mesh_obj(name, verts, faces, material=None, bevel=0.0, coll=False):
    me = bpy.data.meshes.new(name+"_mesh")
    me.from_pydata(verts, [], faces)
    me.update(calc_edges=True)
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if material:
        me.materials.append(material)
    if bevel > 0:
        mod=o.modifiers.new("edge_soften","BEVEL")
        mod.width=bevel
        mod.segments=4 if LOD==0 else 2
        mod.limit_method="ANGLE"
        bpy.context.view_layer.objects.active=o
        try: bpy.ops.object.modifier_apply(modifier=mod.name)
        except: pass
    if coll:
        get_edm_props(o).SPECIAL_TYPE="COLLISION_SHELL"
    return o

def loft_sections(name, sections, material, bevel=.0):
    verts=[]; faces=[]; n=8
    for x,w,zb,zt,cy,cz in sections:
        cy=min(cy,w*.42); cz=min(cz,(zt-zb)*.33)
        ring=[(-w+cy,zb),(w-cy,zb),(w,zb+cz),(w,zt-cz),
              (w-cy,zt),(-w+cy,zt),(-w,zt-cz),(-w,zb+cz)]
        verts.extend((x,y,z) for y,z in ring)
    for i in range(len(sections)-1):
        a=i*n; b=(i+1)*n
        for j in range(n):
            faces.append((a+j,a+(j+1)%n,b+(j+1)%n,b+j))
    faces.append(tuple(range(n-1,-1,-1)))
    off=(len(sections)-1)*n
    faces.append(tuple(off+j for j in range(n)))
    return mesh_obj(name,verts,faces,material,bevel)

def prism_x(name,x0,x1,yz,material,bevel=.008):
    n=len(yz)
    verts=[(x0,y,z) for y,z in yz]+[(x1,y,z) for y,z in yz]
    faces=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]
    for i in range(n):
        faces.append((i,(i+1)%n,n+(i+1)%n,n+i))
    return mesh_obj(name,verts,faces,material,bevel)

def prism_y(name,y0,y1,xz,material,bevel=.006):
    n=len(xz)
    verts=[(x,y0,z) for x,z in xz]+[(x,y1,z) for x,z in xz]
    faces=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]
    for i in range(n):
        faces.append((i,(i+1)%n,n+(i+1)%n,n+i))
    return mesh_obj(name,verts,faces,material,bevel)

def boolean_wheel_well(body,x,r=.485):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64 if LOD==0 else 32,
        radius=r, depth=2.4, location=(x,0,WHEEL_R),
        rotation=(math.radians(90),0,0))
    cut=bpy.context.object
    mod=body.modifiers.new("wheelwell","BOOLEAN")
    mod.operation="DIFFERENCE"
    mod.solver="EXACT"
    mod.object=cut
    bpy.context.view_layer.objects.active=body
    try: bpy.ops.object.modifier_apply(modifier=mod.name)
    except: pass
    bpy.data.objects.remove(cut,do_unlink=True)

def spoke_prism(name, center, side, a, material):
    x0,y0,z0=center
    ux,uz=math.cos(a),math.sin(a)
    tx,tz=-uz,ux
    r0,r1=.072,.178
    w0,w1=.028,.046
    p=[(x0+r0*ux+w0*tx,z0+r0*uz+w0*tz),
       (x0+r1*ux+w1*tx,z0+r1*uz+w1*tz),
       (x0+r1*ux-w1*tx,z0+r1*uz-w1*tz),
       (x0+r0*ux-w0*tx,z0+r0*uz-w0*tz)]
    yf=y0-side*.150
    return prism_y(name,yf-side*.010,yf+side*.010,p,material,.003)
# -------------------------------------------------------------------------------


def wheel(prefix, x, side):
    y = side*(WIDTH/2 + .008)
    z = WHEEL_R
    steer=bpy.data.objects.new(prefix+"_STEER",None)
    steer.location=(x,y,z)
    bpy.context.collection.objects.link(steer)
    roll=bpy.data.objects.new(prefix+"_ROLL",None)
    roll.parent=steer
    roll.location=(0,0,0)
    bpy.context.collection.objects.link(roll)
    if prefix.startswith("FRONT"):
        action_rot(steer,9,2,math.radians(-30),math.radians(30))
    action_rot(roll,8,1,-2*math.pi,2*math.pi)
    bpy.context.scene.frame_set(100)

    tire=torus(prefix+"_TIRE",(x,y,z),.326,.079,M["rubber"],
        rot=(math.radians(90),0,0),
        major_segments=64 if LOD==0 else 32,
        minor_segments=16 if LOD==0 else 8)
    parent_keep(tire,roll)

    rim=cyl(prefix+"_RIM",(x,y-side*.010,z),.205,.268,M["rim"],
        48 if LOD==0 else 24,rot=(math.radians(90),0,0))
    parent_keep(rim,roll)
    lip=torus(prefix+"_RIM_LIP",(x,y-side*.151,z),.181,.012,M["rim_face"],
        rot=(math.radians(90),0,0),
        major_segments=48 if LOD==0 else 24,minor_segments=7)
    parent_keep(lip,roll)
    hub=cyl(prefix+"_CENTER",(x,y-side*.158,z),.066,.024,M["rim"],32,
        rot=(math.radians(90),0,0))
    parent_keep(hub,roll)

    if LOD<2:
        for i in range(6):
            a=i*math.pi/3
            for da in (-.070,.070):
                sp=spoke_prism(f"{prefix}_SPOKE_{i}_{da:+.3f}",(x,y,z),side,a+da,M["rim_face"])
                parent_keep(sp,roll)
        for i in range(6):
            a=2*math.pi*i/6
            lx=x+.050*math.cos(a); lz=z+.050*math.sin(a)
            nut=cyl(f"{prefix}_LUG_{i}",(lx,y-side*.174,lz),.010,.018,M["steel"],12,
                rot=(math.radians(90),0,0))
            parent_keep(nut,roll)

    if LOD==0:
        for i in range(48):
            a=2*math.pi*i/48
            rr=.397
            tx=x+rr*math.cos(a); tz=z+rr*math.sin(a)
            yy=y+side*((i%3)-1)*.055
            lug=box(f"{prefix}_TREAD_{i}",(tx,yy,tz),(.046,.075,.016),M["rubber"],.003,rot=(0,-a,0))
            parent_keep(lug,roll)
    return steer,roll


def add_front():
    bezel=[(-.68,.80),(.68,.80),(.76,.90),(.72,1.28),(.62,1.34),
           (-.62,1.34),(-.72,1.28),(-.76,.90)]
    inner=[(-.60,.87),(.60,.87),(.65,.94),(.62,1.24),(.55,1.28),
           (-.55,1.28),(-.62,1.24),(-.65,.94)]
    prism_x("GRILLE_BEZEL",2.715,2.785,bezel,M["black_plastic"],.018)
    prism_x("GRILLE_INNER",2.775,2.810,inner,M["black_metal"],.010)
    if LOD<2:
        for z in (.97,1.15):
            box(f"GRILLE_BAR_{z}",(2.817,0,z),(.022,1.16,.055),M["black_plastic"],.012)
        rows=(.90,1.04,1.18,1.28) if LOD==0 else (.97,1.18)
        cols=12 if LOD==0 else 8
        for ri,z in enumerate(rows):
            for ci in range(cols):
                y=-.53+ci*(1.06/max(1,cols-1))
                box(f"GRILLE_SLOT_{ri}_{ci}",(2.823,y,z),(.016,.050,.040),M["black_plastic"],.007)
    emblem=torus("TOYOTA_OUTER",(2.842,0,1.08),.112,.016,M["rim_face"],
        rot=(0,math.radians(90),0),major_segments=40,minor_segments=7)
    emblem.scale=(1.0,.76,1.0)
    torus("TOYOTA_INNER",(2.848,0,1.08),.058,.010,M["rim_face"],
        rot=(0,math.radians(90),0),major_segments=28,minor_segments=6)

    for side in (-1,1):
        yz=[(side*.50,1.12),(side*.87,1.12),(side*.91,1.23),
            (side*.84,1.40),(side*.56,1.39),(side*.48,1.28)]
        if side < 0: yz=list(reversed(yz))
        prism_x(f"HEADLAMP_{side}",2.66,2.775,yz,M["headlamp"],.016)
        py=side*.68
        sphere(f"PROJECTOR_CHROME_{side}",(2.790,py,1.28),.082,M["chrome"],26,13)
        sphere(f"PROJECTOR_GLASS_{side}",(2.823,py,1.28),.056,M["headlamp"],22,11)
        box(f"TURN_AMBER_{side}",(2.796,side*.845,1.27),(.028,.072,.105),M["amber"],.018)
        tube(f"DRL_{side}",[(2.825,side*.54,1.17),(2.825,side*.76,1.17),(2.820,side*.82,1.22)],.013,M["white"],1)

    lower=[(-.77,.46),(.77,.46),(.82,.54),(.77,.77),(.65,.82),
           (-.65,.82),(-.77,.77),(-.82,.54)]
    prism_x("FRONT_LOWER_VALANCE",2.72,2.835,lower,M["black_plastic"],.022)
    for side in (-1,1):
        cyl(f"FOG_BEZEL_{side}",(2.850,side*.66,.68),.116,.040,M["black_plastic"],32,rot=(0,math.radians(90),0))
        cyl(f"FOG_{side}",(2.875,side*.66,.68),.080,.050,M["headlamp"],32,rot=(0,math.radians(90),0))
    box("FRONT_LED_BAR",(2.842,0,.805),(.035,.98,.068),M["black_metal"],.010)
    if LOD==0:
        for i in range(18):
            y=-.435+i*(.87/17)
            sphere(f"FRONT_LED_{i}",(2.865,y,.805),.017,M["headlamp"],12,6)
    box("FRONT_CHIN",(2.79,0,.49),(.22,1.42,.20),M["black_plastic"],.045)


def add_body():
    paint=M["burnt"] if DESTROYED else M["paint"]

    # Asymmetric DCLB axle positions: front overhang is shorter than rear.
    global FRONT_AXLE, REAR_AXLE
    FRONT_AXLE=1.800
    REAR_AXLE=FRONT_AXLE-WHEELBASE

    body=loft_sections("BODY_LOWER",[
      (2.78,.74,.53,.97,.10,.10),(2.62,.86,.52,1.16,.09,.10),
      (2.30,.91,.50,1.27,.08,.10),(1.80,.94,.49,1.31,.07,.10),
      (1.24,.93,.50,1.28,.07,.09),(.72,.91,.50,1.20,.06,.08),
      (-.72,.91,.50,1.18,.06,.08),(-1.08,.93,.51,1.16,.06,.08),
      (-2.45,.93,.52,1.15,.06,.08),(-2.73,.89,.54,1.09,.08,.09)
    ],paint,.018)
    boolean_wheel_well(body,FRONT_AXLE,.485)
    boolean_wheel_well(body,REAR_AXLE,.485)

    for sy in (-.52,.52):
        box(f"FRAME_{sy}",(-.10,sy,.39),(4.55,.095,.12),M["steel"],.012)
    cyl("REAR_AXLE",(REAR_AXLE,0,.40),.055,1.52,M["steel"],20,rot=(math.radians(90),0,0))
    sphere("REAR_DIFF",(REAR_AXLE,0,.40),.145,M["steel"],18,9)
    tube("DRIVESHAFT",[(.85,0,.50),(-1.55,0,.42)],.038,M["steel"],1)
    tube("EXHAUST",[(-.35,-.42,.36),(-1.65,-.58,.38),(-2.55,-.64,.43)],.025,M["steel"],1)
    for side in (-1,1):
        tube(f"LEAF_{side}",[(REAR_AXLE-.68,side*.55,.43),(REAR_AXLE,side*.55,.37),(REAR_AXLE+.65,side*.55,.43)],.017,M["steel"],1)

    loft_sections("HOOD_SKIN",[
      (2.56,.77,1.135,1.205,.10,.025),(2.18,.84,1.205,1.285,.09,.025),
      (1.36,.86,1.255,1.335,.08,.025),(1.05,.82,1.245,1.325,.08,.025)
    ],paint,.010)

    loft_sections("CAB_ROOF",[
      (.78,.78,1.69,1.78,.08,.035),(.10,.82,1.72,1.82,.07,.035),
      (-.72,.80,1.69,1.79,.07,.035),(-.91,.76,1.63,1.73,.08,.035)
    ],paint,.012)
    box("WINDSHIELD",(.91,0,1.48),(.055,1.58,.54),M["glass"],.024,rot=(0,math.radians(-18),0))
    box("COWL_BLACK",(1.12,0,1.27),(.16,1.67,.075),M["black_plastic"],.016)

    front_poly=[(.10,1.24),(.88,1.27),(.73,1.68),(.08,1.68)]
    rear_poly=[(-.79,1.23),(.01,1.24),(.01,1.68),(-.72,1.68)]
    for side in (-1,1):
        prism_y(f"FRONT_GLASS_{side}",side*.903,side*.916,front_poly,M["glass"],.006)
        prism_y(f"REAR_GLASS_{side}",side*.903,side*.916,rear_poly,M["glass"],.006)
        box(f"B_PILLAR_{side}",(.045,side*.916,1.46),(.075,.032,.47),M["black_plastic"],.010)
        for sx in (.045,.93,-.86):
            box(f"DOOR_SEAM_{side}_{sx}",(sx,side*.924,.99),(.010,.006,.66),M["black_plastic"],.001)
        for hx in (.52,-.38):
            box(f"DOOR_HANDLE_{side}_{hx}",(hx,side*.938,1.16),(.18,.030,.045),paint,.014)
        box(f"MIRROR_STEM_{side}",(.82,side*1.00,1.42),(.20,.16,.14),M["black_plastic"],.032)
        box(f"MIRROR_CAP_{side}",(.77,side*1.105,1.48),(.30,.18,.18),paint,.055)
        box(f"MIRROR_GLASS_{side}",(.74,side*1.198,1.48),(.20,.010,.125),M["glass"],.022)

    loft_sections("CAMPER_SHELL",[
      (-1.00,.87,1.12,1.28,.05,.04),(-1.35,.89,1.12,1.72,.05,.05),
      (-2.52,.89,1.11,1.72,.05,.05),(-2.69,.84,1.08,1.64,.06,.05)
    ],paint,.014)
    loft_sections("CAMPER_ROOF",[
      (-1.22,.80,1.69,1.80,.08,.035),(-1.90,.84,1.72,1.83,.07,.035),
      (-2.55,.80,1.69,1.79,.08,.035)
    ],paint,.010)
    capwin=[(-2.45,1.28),(-1.22,1.28),(-1.31,1.68),(-2.40,1.68)]
    for side in (-1,1):
        prism_y(f"CAMPER_GLASS_{side}",side*.904,side*.917,capwin,M["glass"],.006)
    box("CAMPER_REAR_GLASS",(-2.685,0,1.46),(.025,1.48,.43),M["glass"],.022)

    for side in (-1,1):
        for axle,label in ((FRONT_AXLE,"FRONT"),(REAR_AXLE,"REAR")):
            pts=[]
            count=31 if LOD==0 else 17
            for i in range(count):
                a=math.radians(10+160*i/(count-1))
                pts.append((axle+.500*math.cos(a),side*.955,.405+.500*math.sin(a)))
            tube(f"{label}_FLARE_{side}",pts,.043,M["black_plastic"],2 if LOD==0 else 1)

    for side in (-1,1):
        tube(f"ROCK_SLIDER_{side}",[(-1.02,side*1.00,.54),(.98,side*1.00,.54)],.042,M["black_metal"],2)
        for x in (-.72,-.05,.64):
            tube(f"ROCK_SLIDER_BRACE_{side}_{x}",[(x,side*.78,.50),(x,side*1.00,.54)],.024,M["black_metal"],1)

    wheel("FRONT_L",FRONT_AXLE,1)
    wheel("FRONT_R",FRONT_AXLE,-1)
    wheel("REAR_L",REAR_AXLE,1)
    wheel("REAR_R",REAR_AXLE,-1)


def add_rack_and_lights():
    if LOD>=2:
        return
    for cx,length,z in ((.15,1.78,1.88),(-1.88,1.45,1.91)):
        for side in (-1,1):
            box(f"RACK_SIDE_{cx}_{side}",(cx,side*.78,z),(length,.052,.105),M["black_metal"],.018)
        bars=8 if LOD==0 else 4
        for i in range(bars):
            x=cx-length*.44+i*(length*.88/max(1,bars-1))
            box(f"RACK_CROSS_{cx}_{i}",(x,0,z+.014),(.038,1.52,.034),M["black_metal"],.007)

    for side in (-1,1):
        x=1.10; y=side*.86; z=1.52
        tube(f"DITCH_BRACKET_{side}",[(1.03,side*.77,1.33),(1.10,y,1.43)],.017,M["black_metal"],1)
        box(f"BLACK_OAK_HOUSING_{side}",(x,y,z),(.15,.18,.16),M["black_metal"],.024)
        face_y=y+side*.096
        for dx in (-.032,.032):
            for dz in (-.032,.032):
                sphere(f"BLACK_OAK_LED_{side}_{dx}_{dz}",(x+dx,face_y,z+dz),.020,M["headlamp"],12,6)
        if LOD==0:
            for i in range(5):
                box(f"BLACK_OAK_FIN_{side}_{i}",(x-.070+i*.035,y-side*.095,z),(.012,.030,.15),M["black_plastic"],.003)


def add_rear():
    paint=M["burnt"] if DESTROYED else M["paint"]
    for side in (-1,1):
        box(f"TAIL_LAMP_{side}",(-2.760,side*.84,1.18),(.12,.17,.38),M["red"],.028)
        box(f"TAIL_REVERSE_{side}",(-2.825,side*.845,1.13),(.025,.13,.075),M["white"],.012)

    box("TAILGATE_FACE",(-2.744,0,1.05),(.055,1.62,.43),paint,.022)
    box("TAILGATE_HANDLE",(-2.780,0,1.20),(.030,.25,.075),M["black_plastic"],.016)
    box("REAR_BUMPER_MAIN",(-2.86,0,.62),(.27,1.86,.25),M["black_metal"],.032)
    for side in (-1,1):
        box(f"REAR_BUMPER_WING_{side}",(-2.82,side*.77,.69),(.32,.36,.30),M["black_metal"],.026,rot=(0,0,math.radians(side*3)))
        box(f"REAR_AMBER_BACKUP_{side}",(-3.005,side*.56,.69),(.025,.20,.095),M["amber"],.012)
        if LOD==0:
            for rr in (-.025,.025):
                for cc in (-.055,0,.055):
                    sphere(f"REAR_AMBER_LED_{side}_{rr}_{cc}",(-3.020,side*.56+cc,.69+rr),.012,M["amber"],10,5)
        torus(f"RECOVERY_RING_{side}",(-3.00,side*.32,.51),.065,.016,M["steel"],rot=(0,math.radians(90),0),major_segments=24,minor_segments=6)
    box("HITCH_RECEIVER",(-3.00,0,.41),(.22,.13,.13),M["black_metal"],.014)


def add_badges_plate_weather():
    if LOD>0:
        return
    for side in (-1,1):
        rot=(-math.pi/2,0,0) if side>0 else (math.pi/2,0,0)
        text_obj("TACOMA",f"SIDE_TACOMA_{side}",(.48,side*.946,1.02),.090,M["black_plastic"],rot=rot)
        text_obj("TRD 4X4",f"TRD_BADGE_{side}",(-2.03,side*.946,1.28),.085,M["black_plastic"],rot=rot)
        text_obj("OFF ROAD",f"TRD_OFFROAD_{side}",(-2.03,side*.946,1.215),.040,M["red"],rot=rot)

    box("DCS_PLATE_FRONT",(2.915,0,.52),(.018,.305,.155),M["white"],.009)
    text_obj("DCS 4X4","DCS_PLATE_FRONT_TEXT",(2.928,0,.52),.055,M["blue"],
             rot=(math.radians(90),0,math.radians(90)))
    box("DCS_PLATE_REAR",(-2.985,0,.70),(.018,.305,.155),M["white"],.009)


def add_interior():
    if LOD>0:
        return
    box("DASH",(.82,0,1.24),(.31,1.36,.18),M["black_plastic"],.035,rot=(0,math.radians(-7),0))
    for x in (.38,-.45):
        for side in (-1,1):
            box(f"SEAT_{x}_{side}",(x,side*.34,1.08),(.40,.42,.48),M["black_plastic"],.068)
            box(f"HEADREST_{x}_{side}",(x-.03,side*.34,1.39),(.23,.28,.18),M["black_plastic"],.045)
    torus("STEERING_WHEEL",(.78,-.32,1.33),.145,.017,M["black_plastic"],
          rot=(0,math.radians(90),0),major_segments=28,minor_segments=7)

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
    bpy.context.scene.frame_start=0
    bpy.context.scene.frame_end=200
    bpy.context.scene.frame_set(100)
    add_body()
    add_front()
    add_rear()
    add_rack_and_lights()
    add_badges_plate_weather()
    add_interior()
    wreck_damage()
    add_collision()
    bpy.context.scene.frame_set(100)
    print(f"[TPG TACOMA V2] built LOD={LOD} destroyed={DESTROYED} objects={len(bpy.context.scene.objects)}")
    print("[TPG TACOMA V2] DCS wheel args: 8 rotation / 9 steering with separate centered pivots")
    print("[TPG TACOMA V2] neutral export frame 100")

build()

# workflow interpolation fix retrigger
