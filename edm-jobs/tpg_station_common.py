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
MATS = {}

def texture(name, base, variation=0.035, stripe=False, size=384, splotch=False):
    path = TEXDIR / (name + ".png")
    if path.exists():
        return path
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    rng = random.Random(zlib.crc32(name.encode("utf-8")) & 0xffffffff)
    px = []
    blotches=[]
    if splotch:
        # Fixed irregular burn/oil staining for the destroyed concrete apron only.
        for _ in range(14):
            blotches.append((
                rng.uniform(.08,.92), rng.uniform(.08,.92),
                rng.uniform(.06,.20), rng.uniform(.05,.17),
                rng.uniform(.52,.86)
            ))
    for y in range(size):
        for x in range(size):
            n = (rng.random() - 0.5) * variation
            if stripe:
                n += 0.020 * math.sin(x * 0.22) + 0.012 * math.sin(y * 0.31)
            dark=0.0
            if splotch:
                u=x/max(1,size-1); v=y/max(1,size-1)
                for cx,cy,rx,ry,intensity in blotches:
                    dx=(u-cx)/rx; dy=(v-cy)/ry
                    d=dx*dx+dy*dy
                    if d < 1.0:
                        edge=max(0.0,1.0-d)
                        irregular=.78+.22*math.sin((x+y)*.19+cx*17.0)
                        dark=max(dark,intensity*edge*edge*irregular)
                # fine soot freckles around larger stains
                if rng.random() > .985:
                    dark=max(dark,rng.uniform(.18,.48))
            px.extend((
                max(0.0, min(1.0, (base[0] + n) * (1.0-dark))),
                max(0.0, min(1.0, (base[1] + n) * (1.0-dark))),
                max(0.0, min(1.0, (base[2] + n) * (1.0-dark))),
                1.0
            ))
    img.pixels = px
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    return path

def edm_mat(name, color, rough=0.7, metal=0.0, variation=0.035, stripe=False, splotch=False,
            emissive_color=None, emissive_value=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    group = createEdmNodeGroup("EDM_Default_Material", m)
    group.post_init(MAT_DESCS["EDM_Default_Material"])
    group.name = "Group"
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(texture(name, color, variation, stripe, 384, splotch)), check_existing=True)
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
    if emissive_color is not None:
        # Official ED default material: constant self-illumination color plus intensity.
        # Keep an ordinary bright albedo for daylight readability, then let the EDM
        # emissive block carry the digits through dusk/night independently of scene light.
        group.inputs[NodeSocketInDefaultEnum.EMISSIVE].default_value = (*emissive_color, 1.0)
        group.inputs[NodeSocketInDefaultEnum.EMISSIVE_VALUE].default_value = float(emissive_value)
    return m

def mats():
    if MATS:
        return MATS
    MATS.update({
        "asphalt": edm_mat("TPG_GASSTATION110_Asphalt",(0.115,0.122,0.126),0.95,0.0,0.065,True),
        "concrete": edm_mat("TPG_GASSTATION110_Concrete",(0.49,0.495,0.475),0.90,0.0,0.050,True),
        "damaged_base": edm_mat("TPG_GASSTATION110_DamagedBase",(0.235,0.245,0.245),0.95,0.0,0.045,True,True),
        "stucco": edm_mat("TPG_GASSTATION110_Stucco",(0.70,0.665,0.585),0.84,0.0,0.038,True),
        "white": edm_mat("TPG_GASSTATION110_PaintedWhite",(0.79,0.80,0.77),0.58,0.02,0.022),
        "red": edm_mat("TPG_GASSTATION110_BrandRed",(0.44,0.026,0.020),0.43,0.08,0.020),
        "charcoal": edm_mat("TPG_GASSTATION110_Charcoal",(0.050,0.055,0.060),0.56,0.04,0.018),
        "metal": edm_mat("TPG_GASSTATION110_Metal",(0.30,0.315,0.325),0.31,0.74,0.020),
        "aluminum": edm_mat("TPG_GASSTATION110_Aluminum",(0.49,0.50,0.50),0.28,0.82,0.018),
        "glass": edm_mat("TPG_GASSTATION110_Glass",(0.050,0.115,0.145),0.18,0.10,0.010),
        "rubber": edm_mat("TPG_GASSTATION110_Rubber",(0.018,0.020,0.021),0.94,0.0,0.015),
        "screen": edm_mat("TPG_GASSTATION110_Screen",(0.025,0.055,0.044),0.26,0.05,0.008),
        "yellow": edm_mat("TPG_GASSTATION110_SafetyYellow",(0.72,0.49,0.035),0.64,0.02,0.025),
        "blue": edm_mat("TPG_GASSTATION110_StickerBlue",(0.035,0.22,0.42),0.52,0.02,0.015),
        "green": edm_mat("TPG_GASSTATION110_StickerGreen",(0.045,0.36,0.13),0.56,0.01,0.015),
        "price_led": edm_mat("TPG_GASSTATION110_PriceLED",(0.16,0.92,0.24),0.30,0.01,0.010,
                             emissive_color=(0.08,1.0,0.16), emissive_value=2.35),
        "orange": edm_mat("TPG_GASSTATION110_StickerOrange",(0.82,0.26,0.025),0.55,0.01,0.018),
        "cream": edm_mat("TPG_GASSTATION110_Cream",(0.88,0.82,0.66),0.66,0.0,0.020),
        "interior": edm_mat("TPG_GASSTATION110_InteriorDark",(0.075,0.070,0.060),0.78,0.01,0.020),
        "soot": edm_mat("TPG_GASSTATION110_Soot",(0.018,0.014,0.012),0.96,0.01,0.070,True),
        "char": edm_mat("TPG_GASSTATION110_Char",(0.045,0.026,0.017),0.92,0.02,0.085,True),
        "rust": edm_mat("TPG_GASSTATION110_Rust",(0.24,0.075,0.025),0.88,0.05,0.065,True),
        "cyan": edm_mat("TPG_GASSTATION110_AdCyan",(0.025,0.42,0.56),0.50,0.01,0.012),
        "purple": edm_mat("TPG_GASSTATION110_AdPurple",(0.31,0.045,0.42),0.52,0.01,0.014),
    })
    return MATS

def box(name, loc, scale, mat, bevel=0.05, coll=False, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new("edge_soften","BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if mat:
        o.data.materials.append(mat)
    if coll:
        get_edm_props(o).SPECIAL_TYPE = "COLLISION_SHELL"
    return o

def cyl(name, loc, radius, depth, mat, verts=16, coll=False, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    if coll:
        get_edm_props(o).SPECIAL_TYPE = "COLLISION_SHELL"
    return o

def sphere(name, loc, radius, mat, seg=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=radius, location=loc)
    o=bpy.context.object; o.name=name
    if mat: o.data.materials.append(mat)
    return o

def torus(name, loc, major_radius, minor_radius, mat, rot=(0,0,0), major_segments=20, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(major_radius=major_radius, minor_radius=minor_radius,
        major_segments=major_segments, minor_segments=minor_segments, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name
    if mat: o.data.materials.append(mat)
    return o

def bolt(name, loc, mat, rot=(math.radians(90),0,0), radius=.018, depth=.018):
    return cyl(name,loc,radius,depth,mat,8,False,rot)

def text_obj(text, name, loc, size, mat, rot=(math.radians(90),0,0), extrude=.012, align="CENTER"):
    c = bpy.data.curves.new(name + "_curve","FONT")
    c.body = text
    c.align_x = align
    c.align_y = "CENTER"
    c.size = size
    c.extrude = extrude
    c.bevel_depth = .003
    c.bevel_resolution = 1
    o = bpy.data.objects.new(name,c)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(mat)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.object
    o.name = name
    return o

def hose(name, points, mat, radius=.030):
    crv = bpy.data.curves.new(name+"_curve","CURVE")
    crv.dimensions = "3D"
    crv.bevel_depth = radius
    crv.bevel_resolution = 2
    spl = crv.splines.new("BEZIER")
    spl.bezier_points.add(len(points)-1)
    for bp,co in zip(spl.bezier_points, points):
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name,crv)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.object

def decal_panel(name, text, loc, dims, panel_mat, text_mat, size=.18):
    box(name+"_PANEL", loc, dims, panel_mat, .008)
    text_obj(text, name+"_TEXT", (loc[0],loc[1]-.026,loc[2]), size, text_mat,
             rot=(math.radians(90),0,0), extrude=.006)

def add_ground_markings(M):
    # Painted lane/parking markings sit only millimeters above asphalt to avoid z-fighting.
    for x in (-11.0,-7.2,-3.4,0.4,4.2,8.0,11.8):
        box("PARK_LINE_"+str(x),(x,5.55,.062),(.09,4.2,.022),M["cream"],.0)
    box("STOP_BAR",(0,2.75,.063),(12.5,.10,.024),M["cream"],.0)
    # storm drains with slat geometry
    for x in (-11.8,11.8):
        box("DRAIN_FRAME_"+str(x),(x,-9.8,.078),(2.0,.75,.055),M["charcoal"],.015)
        for i in range(8):
            box("DRAIN_SLAT_"+str(x)+"_"+str(i),(x-0.78+i*.22,-9.8,.112),(.085,.64,.018),M["metal"],.004)

def build_pump(x,y,idx,M):
    # High-detail modern dispenser. Four physical cabinets, each modeled as real hardware.
    box(f"P{idx}_island",(x,y,.18),(2.95,1.42,.36),M["concrete"],.12)
    box(f"P{idx}_curb_inset",(x,y,.365),(2.58,1.12,.07),M["charcoal"],.025)
    box(f"P{idx}_cabinet",(x,y,1.36),(1.06,.74,2.34),M["white"],.07)
    box(f"P{idx}_toe",(x,y,.34),(1.10,.78,.27),M["charcoal"],.022)
    box(f"P{idx}_top",(x,y,2.38),(1.12,.80,.31),M["red"],.04)
    box(f"P{idx}_cap",(x,y,2.555),(1.17,.83,.075),M["charcoal"],.015)

    # cabinet seams, corner trim and fasteners
    for sx in (-.49,.49):
        box(f"P{idx}_VERT_TRIM_{sx}",(x+sx,y,1.37),(.035,.765,2.22),M["aluminum"],.006)
    for z in (.53,2.16):
        box(f"P{idx}_SERVICE_SEAM_{z}",(x,y-.381,z),(.88,.015,.018),M["charcoal"],.0)
    for sx in (-.43,.43):
        for z in (.48,2.22):
            bolt(f"P{idx}_CAB_BOLT_{sx}_{z}",(x+sx,y-.389,z),M["metal"],radius=.014,depth=.014)

    for side,sy in (("A",-0.382),("B",0.382)):
        face_y=y+sy
        outward=-1 if sy<0 else 1
        yy=face_y+outward*.010

        # payment/readout bay
        box(f"P{idx}_{side}_recess",(x,yy,1.60),(.84,.035,.75),M["charcoal"],.012)
        box(f"P{idx}_{side}_screen_bezel",(x,yy+outward*.010,1.84),(.56,.025,.28),M["aluminum"],.006)
        box(f"P{idx}_{side}_screen",(x,yy+outward*.024,1.84),(.49,.018,.21),M["screen"],.003)
        text_obj("WELCOME",f"P{idx}_{side}_SCREEN_TEXT",(x,yy+outward*.038,1.84),.085,M["green"],
                 rot=(math.radians(90),0,0),extrude=.004)

        box(f"P{idx}_{side}_card_bezel",(x-.265,yy+outward*.018,1.49),(.18,.028,.19),M["aluminum"],.005)
        box(f"P{idx}_{side}_card_slot",(x-.265,yy+outward*.035,1.49),(.115,.012,.025),M["charcoal"],.001)
        box(f"P{idx}_{side}_keypad_bezel",(x+.245,yy+outward*.018,1.49),(.28,.028,.24),M["aluminum"],.005)
        for rr in range(3):
            for cc in range(3):
                box(f"P{idx}_{side}_KEY_{rr}_{cc}",(x+.17+cc*.075,yy+outward*.036,1.55-rr*.065),
                    (.045,.012,.038),M["charcoal"],.002)

        # Realistic grade strip: label, octane number and selection button in a row.
        grade_x=(-.29,0,.29)
        grade_data=(("REG","87","green"),("PLUS","89","cream"),("PREM","93","red"))
        for j,(dx,(label,octane,matname)) in enumerate(zip(grade_x,grade_data)):
            box(f"P{idx}_{side}_GRADE_PLATE_{j}",(x+dx,yy+outward*.018,1.14),(.245,.028,.25),M["white"],.004)
            box(f"P{idx}_{side}_GRADE_COLOR_{j}",(x+dx,yy+outward*.034,1.20),(.215,.012,.075),M[matname],.002)
            text_obj(octane,f"P{idx}_{side}_OCTANE_{j}",(x+dx,yy+outward*.050,1.10),.105,M["charcoal"],
                     rot=(math.radians(90),0,0),extrude=.004)
            text_obj(label,f"P{idx}_{side}_GRADE_LABEL_{j}",(x+dx,yy+outward*.052,1.26),.052,M["charcoal"],
                     rot=(math.radians(90),0,0),extrude=.003)
            box(f"P{idx}_{side}_GRADE_BUTTON_{j}",(x+dx,yy+outward*.042,.965),(.19,.025,.085),M[matname],.018)

        decal_panel(f"P{idx}_{side}_PAY","PAY HERE",(x,yy+outward*.015,2.20),(.60,.025,.18),M["blue"],M["white"],.095)
        decal_panel(f"P{idx}_{side}_NO_SMOKE","NO SMOKING",(x,yy+outward*.015,.72),(.68,.025,.19),M["cream"],M["charcoal"],.085)

        # Hose cradle/fitting on right side of each face.
        hx=x+.62
        box(f"P{idx}_{side}_HOSE_CRADLE",(hx,yy+outward*.02,1.73),(.13,.16,.48),M["charcoal"],.018)
        cyl(f"P{idx}_{side}_SWIVEL",(hx,yy+outward*.115,1.93),.055,.12,M["metal"],16,
            rot=(math.radians(90),0,0))
        cyl(f"P{idx}_{side}_BREAKAWAY",(hx,yy+outward*.17,2.01),.048,.16,M["aluminum"],16,
            rot=(math.radians(90),0,0))
        hose(f"P{idx}_{side}_hose",[(hx,yy+outward*.16,2.02),(x+.82,yy+outward*.30,1.58),
             (x+.77,yy+outward*.35,.85),(x+.68,yy+outward*.29,.62)],M["rubber"],.027)

        # Nozzle body, trigger guard, lever, metal spout and boot.
        nz=(x+.66,yy+outward*.30,.72)
        box(f"P{idx}_{side}_NOZZLE_GRIP",nz,(.16,.11,.39),M["charcoal"],.035,rot=(0,math.radians(-11),0))
        box(f"P{idx}_{side}_NOZZLE_HEAD",(x+.66,yy+outward*.30,.91),(.23,.15,.17),M["charcoal"],.045,
            rot=(0,math.radians(-8),0))
        torus(f"P{idx}_{side}_TRIGGER_GUARD",(x+.66,yy+outward*.37,.75),.11,.018,M["metal"],
              rot=(math.radians(90),0,0),major_segments=16,minor_segments=6)
        box(f"P{idx}_{side}_TRIGGER",(x+.66,yy+outward*.385,.78),(.035,.025,.14),M["aluminum"],.008,
            rot=(0,math.radians(-16),0))
        cyl(f"P{idx}_{side}_SPOUT",(x+.73,yy+outward*.31,1.03),.025,.32,M["aluminum"],14,
            rot=(0,math.radians(58),0))
        cyl(f"P{idx}_{side}_NOZZLE_BOOT",(x+.66,yy+outward*.255,.67),.048,.12,M["rubber"],14,
            rot=(math.radians(90),0,0))

    # Island protection with caps/base plates and anchor bolts.
    for bx in (-1.10,1.10):
        box(f"P{idx}_BOLLARD_BASE_{bx}",(x+bx,y,.08),(.30,.30,.07),M["metal"],.025)
        cyl(f"P{idx}_bollard_{bx}",(x+bx,y,.64),.095,1.22,M["yellow"],16)
        sphere(f"P{idx}_bollard_cap_{bx}",(x+bx,y,1.25),.10,M["yellow"],16,8)
        for ax in (-.10,.10):
            for ay in (-.10,.10):
                bolt(f"P{idx}_ANCHOR_{bx}_{ax}_{ay}",(x+bx+ax,y+ay,.125),M["metal"],
                     rot=(0,0,0),radius=.018,depth=.025)


def build_price_sign(M):
    # Full pylon cabinet with real frame depth, trim, divider rails, footer branding and fasteners.
    for x in (-15.62,-13.78):
        box("PRICE_FOOT_"+str(x),(x,7.8,.20),(.88,.96,.40),M["concrete"],.07)
        box("PRICE_POST_"+str(x),(x,7.8,3.72),(.24,.34,7.08),M["charcoal"],.025)
        box("PRICE_POST_TRIM_"+str(x),(x,7.61,3.72),(.10,.025,6.86),M["aluminum"],.006)
        box("PRICE_POST_CAP_"+str(x),(x,7.8,7.30),(.31,.41,.16),M["metal"],.018)
        for z in (.28,1.2):
            bolt("PRICE_POST_BOLT_"+str(x)+"_"+str(z),(x,7.61,z),M["metal"],radius=.017,depth=.015)

    box("PRICE_CABINET",(-14.7,7.8,6.37),(4.52,.54,4.05),M["charcoal"],.085)
    box("PRICE_FACE",(-14.7,7.50,6.37),(4.18,.045,3.72),M["white"],.012)
    box("PRICE_HEADER",(-14.7,7.465,7.63),(4.12,.025,.92),M["red"],.008)
    text_obj("TPG","PRICE_TPG",(-14.7,7.43,7.73),.76,M["white"],extrude=.022)
    # Larger and better centered subtitle, per screenshot.
    text_obj("FUEL + LUUUUBE","PRICE_SUB",(-14.7,7.425,7.08),.34,M["charcoal"],extrude=.014)

    labels=(("REGULAR","87","3.95","green"),("PLUS","89","4.15","cream"),("PREMIUM","93","4.45","red"))
    zs=(6.42,5.70,4.98)
    for i,((grade,octane,price,matname),z) in enumerate(zip(labels,zs)):
        box("PRICE_ROW_"+str(i),(-14.7,7.455,z),(3.86,.030,.56),M["interior"],.004)
        text_obj(grade,"PRICE_GRADE_"+str(i),(-15.45,7.425,z+.11),.145,M["cream"],extrude=.006)
        text_obj(octane,"PRICE_OCTANE_"+str(i),(-15.42,7.425,z-.12),.19,M[matname],extrude=.007)
        text_obj(price,"PRICE_VALUE_"+str(i),(-13.83,7.425,z),.39,M["price_led"],extrude=.010)
        box("PRICE_DIV_"+str(i),(-14.7,7.44,z-.32),(3.80,.018,.018),M["aluminum"],.0)

    box("PRICE_FOOTER",(-14.7,7.46,4.36),(3.90,.028,.42),M["blue"],.005)
    text_obj("OPEN 24-ish  |  AIR  |  ICE","PRICE_FOOTER_TEXT",(-14.7,7.425,4.36),.125,M["white"],extrude=.006)
    box("PRICE_HATCH",(-14.7,8.085,4.63),(1.35,.05,.48),M["metal"],.012)
    box("PRICE_HATCH_HANDLE",(-14.7,8.12,4.63),(.34,.04,.07),M["charcoal"],.01)
    for x in (-16.70,-12.70):
        for z in (4.45,8.27):
            bolt("PRICE_FASTENER_"+str(x)+"_"+str(z),(x,7.43,z),M["metal"],radius=.032,depth=.024)


def build_storefront(M, detail=True):
    box("STORE",(0,8.0,2.10),(17.4,7.4,4.2),M["stucco"],.10)
    box("STORE_PARAPET",(0,8.0,4.42),(17.8,7.8,.62),M["white"],.07)
    box("STORE_RED_BAND",(0,4.27,3.78),(17.8,.16,.46),M["red"],.018)
    box("STORE_INTERIOR",(0,4.95,2.05),(14.8,.12,2.65),M["interior"],.008)

    windows=[(-6.55,1.65),(-4.55,1.65),(-2.55,1.65),(2.55,1.65),(4.55,1.65),(6.55,1.65)]
    for i,(x,w) in enumerate(windows):
        box(f"GLASS_{i}",(x,4.305,2.10),(w,.045,2.62),M["glass"],.008)
        for xx in (x-w/2-.035,x+w/2+.035):
            box(f"FRAME_V_{i}_{xx}",(xx,4.275,2.10),(.075,.075,2.76),M["charcoal"],.008)
        for zz in (.73,3.47):
            box(f"FRAME_H_{i}_{zz}",(x,4.275,zz),(w+.14,.075,.075),M["charcoal"],.008)

    # Proper poster artwork assembled from layered geometry rather than plain colored rectangles.
    if detail:
        # Tactical Taquitos: product badge + flame stripe + price burst.
        box("AD_TACO_FRAME",(-6.55,4.235,2.18),(1.28,.035,.92),M["charcoal"],.018)
        box("AD_TACO_BG",(-6.55,4.210,2.18),(1.18,.018,.82),M["orange"],.004)
        box("AD_TACO_STRIPE",(-6.55,4.195,2.46),(1.05,.012,.12),M["red"],.002)
        text_obj("TACTICAL","AD_TACO_T1",(-6.55,4.175,2.48),.14,M["cream"],extrude=.005)
        text_obj("TAQUITOS","AD_TACO_T2",(-6.55,4.175,2.24),.18,M["white"],extrude=.006)
        text_obj("2 FOR $3.49","AD_TACO_PRICE",(-6.55,4.175,1.95),.13,M["cream"],extrude=.005)
        for j in (-.30,0,.30):
            cyl("AD_TACO_ROLL_"+str(j),(-6.55+j,4.17,2.08),.045,.34,M["cream"],12,
                rot=(math.radians(90),0,0))

        # Coffee poster: cup silhouette, steam lines, actual promo hierarchy.
        box("AD_COFFEE_FRAME",(-4.55,4.235,2.18),(1.28,.035,.92),M["charcoal"],.018)
        box("AD_COFFEE_BG",(-4.55,4.210,2.18),(1.18,.018,.82),M["charcoal"],.004)
        text_obj("HOT COFFEE","AD_COFFEE_T1",(-4.55,4.175,2.47),.15,M["cream"],extrude=.005)
        box("AD_CUP",(-4.55,4.17,2.16),(.38,.018,.30),M["cream"],.03)
        torus("AD_CUP_HANDLE",(-4.31,4.17,2.18),.10,.025,M["cream"],rot=(math.radians(90),0,0),major_segments=14,minor_segments=5)
        for j in (-.10,.10):
            hose("AD_STEAM_"+str(j),[(-4.55+j,4.16,2.33),(-4.60+j,4.16,2.44),(-4.53+j,4.16,2.54)],M["cream"],.009)
        text_obj("BAD DECISIONS","AD_COFFEE_T2",(-4.55,4.175,1.91),.105,M["orange"],extrude=.004)

        # Lottery poster: ticket cards + starburst feel.
        box("AD_LOTTO_FRAME",(4.55,4.235,2.18),(1.28,.035,.92),M["charcoal"],.018)
        box("AD_LOTTO_BG",(4.55,4.210,2.18),(1.18,.018,.82),M["green"],.004)
        text_obj("LUCKY-ish","AD_LOTTO_T1",(4.55,4.175,2.47),.17,M["cream"],extrude=.006)
        for j in (-.28,0,.28):
            box("AD_TICKET_"+str(j),(4.55+j,4.17,2.18),(.22,.012,.30),M["cream"],.01,rot=(0,math.radians(j*12),0))
            text_obj("$","AD_TICKET_DOLLAR_"+str(j),(4.55+j,4.155,2.18),.11,M["green"],extrude=.003)
        text_obj("TICKETS","AD_LOTTO_T2",(4.55,4.175,1.92),.16,M["cream"],extrude=.005)

        # Wiper poster: windshield, wiper arm and rain droplets.
        box("AD_WIPER_FRAME",(6.55,4.235,2.18),(1.28,.035,.92),M["charcoal"],.018)
        box("AD_WIPER_BG",(6.55,4.210,2.18),(1.18,.018,.82),M["blue"],.004)
        text_obj("BUGS LOST.","AD_WIPER_T1",(6.55,4.175,2.47),.14,M["white"],extrude=.005)
        box("AD_WINDSHIELD",(6.55,4.17,2.18),(.78,.012,.30),M["cyan"],.03)
        box("AD_WIPER_ARM",(6.55,4.15,2.16),(.62,.014,.035),M["charcoal"],.006,rot=(0,math.radians(-16),0))
        for j in (-.28,0,.28):
            sphere("AD_DROP_"+str(j),(6.55+j,4.145,2.30),.025,M["cream"],10,6)
        text_obj("WINDSHIELD WON.","AD_WIPER_T2",(6.55,4.175,1.92),.095,M["white"],extrude=.004)

    # centered double door and hardware
    for dx in (-.44,.44):
        box("DOOR_GLASS_"+str(dx),(dx,4.285,1.78),(.78,.05,3.20),M["glass"],.008)
        box("DOOR_HANDLE_"+str(dx),(dx + (.22 if dx<0 else -.22),4.205,1.80),(.045,.055,.82),M["metal"],.008)
        box("DOOR_KICK_"+str(dx),(dx,4.205,.56),(.70,.025,.34),M["aluminum"],.006)
    for xx in (-.88,0,.88):
        box("DOOR_FRAME_"+str(xx),(xx,4.255,1.78),(.085,.08,3.38),M["charcoal"],.008)
    box("DOOR_FRAME_T",(0,4.255,3.45),(1.84,.08,.09),M["charcoal"],.008)
    box("DOOR_THRESHOLD",(0,4.19,.16),(1.88,.32,.10),M["metal"],.02)
    decal_panel("DOOR_HOURS","OPEN 24-ish",(0,4.215,2.55),(1.18,.024,.28),M["blue"],M["white"],.13)
    decal_panel("DOOR_PUSH","PUSH",(.43,4.215,1.72),(.26,.024,.14),M["cream"],M["charcoal"],.095)

    # larger, more centered storefront sign cabinet
    box("STORE_SIGN_CABINET",(0,4.145,4.11),(9.80,.20,.88),M["charcoal"],.045)
    box("STORE_SIGN_FACE",(0,4.025,4.11),(9.48,.028,.68),M["red"],.006)
    text_obj("TPG FUEL + LUUUUBE","STORE_SIGN",(0,3.985,4.11),.54,M["white"],extrude=.020)

    if detail:
        box("ATM",(7.45,4.02,1.02),(1.05,.60,1.88),M["blue"],.06)
        box("ATM_SCREEN",(7.45,3.70,1.34),(.65,.028,.42),M["screen"],.006)
        text_obj("ATM","ATM_TEXT",(7.45,3.66,1.76),.18,M["white"],extrude=.008)
        box("ICE_CHEST",(-7.60,4.0,.74),(1.75,.95,1.45),M["white"],.06)
        decal_panel("ICE_LABEL","ICE",(-7.60,3.50,.95),(1.25,.025,.48),M["blue"],M["white"],.28)
        box("PAPER_BOX",(-6.05,3.92,.58),(.72,.70,1.10),M["green"],.04)
        text_obj("NEWS","PAPER_TEXT",(-6.05,3.54,.72),.16,M["white"],extrude=.007)
        cyl("FRONT_TRASH",(6.15,3.80,.60),.34,1.20,M["charcoal"],18)
        box("FIRE_CAB",(8.18,4.00,1.10),(.48,.26,1.08),M["red"],.035)
        text_obj("FIRE","FIRE_TEXT",(8.18,3.85,1.18),.12,M["white"],extrude=.006)


def build_canopy(M, detail=True):
    # canopy is intentionally slightly sloped/trimmed but grounded on columns
    box("CANOPY",(0,-3.35,5.20),(25.6,13.9,.54),M["white"],.10)
    box("CANOPY_RED_FRONT",(0,-10.26,5.24),(25.7,.24,.58),M["red"],.025)
    box("CANOPY_RED_REAR",(0,3.56,5.24),(25.7,.24,.44),M["red"],.025)
    box("CANOPY_SIDE_L",(-12.74,-3.35,5.24),(.22,13.45,.44),M["white"],.025)
    box("CANOPY_SIDE_R",(12.74,-3.35,5.24),(.22,13.45,.44),M["white"],.025)
    box("CANOPY_SIGN_CAB",(0,-10.405,5.24),(9.6,.10,.40),M["charcoal"],.012)
    text_obj("TPG FUEL + LUUUUBE","CANOPY_SIGN",(0,-10.47,5.23),.42,M["white"],extrude=.014)

    # six columns provide convincing span support
    for x in (-10.6,0,10.6):
        for y in (-7.9,1.25):
            box("COLUMN_"+str(x)+"_"+str(y),(x,y,2.58),(.42,.42,5.16),M["white"],.045)
            box("COLUMN_BASE_"+str(x)+"_"+str(y),(x,y,.16),(.82,.82,.32),M["concrete"],.07)
            # protective wrap at vehicle height
            box("COLUMN_GUARD_"+str(x)+"_"+str(y),(x,y,.78),(.58,.58,1.05),M["yellow"],.05)
    if detail:
        # soffit panels, fluorescent fixtures and structural seams
        for x in (-9,-6,-3,0,3,6,9):
            box("SOFFIT_SEAM_"+str(x),(x,-3.35,4.91),(.025,12.8,.025),M["charcoal"],.0)
        for x in (-8,-4,0,4,8):
            for y in (-7.0,.2):
                box("CANOPY_LIGHT_"+str(x)+"_"+str(y),(x,y,4.90),(1.25,.42,.035),M["cream"],.004)

def build_misc(M, detail=True):
    for x in (-8.7,-5.9,-3.1,3.1,5.9,8.7):
        box("WHEEL_STOP_"+str(x),(x,3.20,.17),(1.65,.24,.22),M["concrete"],.04)

    box("AIRVAC_PAD",(10.8,3.4,.12),(3.6,2.0,.24),M["concrete"],.06)
    box("AIRVAC",(10.4,3.4,.95),(1.05,.78,1.75),M["blue"],.07)
    text_obj("AIR + VAC","AIRVAC_TEXT",(10.4,2.99,1.20),.15,M["white"],extrude=.008)
    hose("AIR_HOSE",[(10.80,3.4,1.25),(11.25,3.10,.70),(11.55,3.25,.16)],M["rubber"],.024)
    box("PROPANE_CAGE",(8.8,3.4,.85),(1.45,.85,1.70),M["metal"],.025)
    for i in range(4):
        cyl("PROPANE_"+str(i),(8.45+(i%2)*.65,3.42,.48+(i//2)*.72),.16,.62,M["white"],14)
    decal_panel("PROPANE_SIGN","PROPANE",(8.8,2.955,1.50),(1.20,.024,.30),M["red"],M["white"],.14)

    box("DUMPSTER_PAD",(6.0,12.2,.10),(5.0,2.4,.20),M["concrete"],.04)
    box("DUMPSTER",(6.0,12.2,.90),(2.8,1.45,1.65),M["green"],.06)
    box("DUMPSTER_LID",(6.0,12.2,1.78),(2.95,1.55,.14),M["charcoal"],.025)

    # Actual rooftop datum: top of STORE_PARAPET is 4.73. Equipment curbs start ON it, not above it.
    roof_z=4.74
    for unit,x in enumerate((-5.0,0,5.0),1):
        # curb / flashing
        box(f"HVAC_{unit}_CURB",(x,8.15,roof_z+.10),(2.30,1.68,.20),M["charcoal"],.025)
        box(f"HVAC_{unit}_FLASHING",(x,8.15,roof_z+.20),(2.42,1.80,.08),M["aluminum"],.018)
        # RTU cabinet split into condenser/economizer sections
        box(f"HVAC_{unit}_BODY",(x,8.15,roof_z+.62),(2.20,1.55,.82),M["metal"],.055)
        box(f"HVAC_{unit}_TOP",(x,8.15,roof_z+1.07),(2.24,1.59,.10),M["aluminum"],.025)
        box(f"HVAC_{unit}_PANEL",(x-.61,7.365,roof_z+.64),(.78,.035,.58),M["charcoal"],.005)
        # louver blades
        for i in range(7):
            box(f"HVAC_{unit}_LOUVER_{i}",(x-.92+i*.205,7.335,roof_z+.58),(.145,.022,.045),M["charcoal"],.004,
                rot=(math.radians(8),0,0))
        # round top condenser fan grille
        torus(f"HVAC_{unit}_FAN_RING",(x+.47,8.15,roof_z+1.135),.37,.025,M["charcoal"],major_segments=24,minor_segments=6)
        for a in range(0,180,30):
            box(f"HVAC_{unit}_FAN_BAR_{a}",(x+.47,8.15,roof_z+1.142),(.72,.025,.018),M["charcoal"],.002,
                rot=(0,0,math.radians(a)))
        cyl(f"HVAC_{unit}_FAN_HUB",(x+.47,8.15,roof_z+1.15),.085,.035,M["charcoal"],16)
        # access-panel screws down to individual fasteners
        for sx in (-1.02,-.20,.20,1.02):
            for zoff in (.30,.88):
                bolt(f"HVAC_{unit}_SCREW_{sx}_{zoff}",(x+sx,7.325,roof_z+zoff),M["aluminum"],radius=.012,depth=.012)
        # small electrical disconnect and conduit
        box(f"HVAC_{unit}_DISCONNECT",(x+1.22,8.48,roof_z+.55),(.28,.18,.40),M["cream"],.018)
        hose(f"HVAC_{unit}_CONDUIT",[(x+1.22,8.52,roof_z+.34),(x+1.30,8.62,roof_z+.22),(x+1.42,8.65,roof_z+.16)],M["metal"],.018)

    # Roof vents attached with boots, risers, caps and fasteners.
    for n,x in enumerate((-3.2,3.2),1):
        box(f"VENT_{n}_BOOT",(x,9.55,roof_z+.045),(.62,.62,.09),M["charcoal"],.018)
        cyl(f"VENT_{n}_RISER",(x,9.55,roof_z+.31),.21,.52,M["metal"],20)
        cyl(f"VENT_{n}_CAP",(x,9.55,roof_z+.60),.30,.08,M["aluminum"],20)
        cyl(f"VENT_{n}_TOP",(x,9.55,roof_z+.66),.18,.05,M["charcoal"],20)
        for a in range(0,360,90):
            bolt(f"VENT_{n}_SCREW_{a}",(x+math.cos(math.radians(a))*.24,9.55+math.sin(math.radians(a))*.24,roof_z+.095),
                 M["aluminum"],rot=(0,0,0),radius=.012,depth=.012)

    # parapet coping fasteners / roof drain scuppers
    for x in (-7,-3.5,0,3.5,7):
        bolt("PARAPET_SCREW_"+str(x),(x,4.08,4.73),M["aluminum"],rot=(0,0,0),radius=.012,depth=.012)
    box("ROOF_SCUPPER_L",(-7.2,4.05,4.42),(.48,.24,.28),M["charcoal"],.018)
    box("ROOF_SCUPPER_R",(7.2,4.05,4.42),(.48,.24,.28),M["charcoal"],.018)

    if detail:
        box("A_FRAME_LEG_L",(-8.3,3.60,.48),(.10,.50,.92),M["metal"],.02,rot=(0,math.radians(-12),0))
        box("A_FRAME_LEG_R",(-7.55,3.60,.48),(.10,.50,.92),M["metal"],.02,rot=(0,math.radians(12),0))
        box("A_FRAME_FACE",(-7.92,3.35,.78),(1.15,.06,.82),M["orange"],.02)
        text_obj("NO AFTERBURNER\nUNDER CANOPY","A_FRAME_TEXT",(-7.92,3.30,.79),.105,M["cream"],extrude=.006)
        box("SERVICE_DOOR",(7.0,11.72,1.55),(1.15,.08,2.85),M["charcoal"],.018)
        box("METER_BOX",(8.15,11.75,1.48),(.55,.30,.78),M["metal"],.025)
        cyl("METER_FACE",(8.15,11.58,1.62),.17,.06,M["glass"],16,rot=(math.radians(90),0,0))


def build_destroyed(M):
    # Fire-damaged v1.2 state: preserve the structural collapse but make the burn history unmistakable.
    box("FORECOURT",(0,0,.025),(38,28,.05),M["asphalt"],.012)
    box("APRON",(0,-1.0,.02),(27,18,.08),M["damaged_base"],.025)
    add_ground_markings(M)

    # Core ruin is soot-blackened, with brown-char transitions and surviving red/white fragments.
    box("DEST_STORE_CORE",(-1.0,8.2,1.48),(13.2,6.6,2.85),M["soot"],.06,
        rot=(math.radians(1.5),math.radians(-2.0),math.radians(-1.5)))
    box("DEST_STORE_CHAR_LAYER",(-.7,4.85,1.60),(11.8,.22,2.55),M["char"],.025,
        rot=(math.radians(1),0,math.radians(-1)))
    box("DEST_STORE_WALL_L",(-7.2,7.1,.92),(3.2,1.0,1.65),M["char"],.035,
        rot=(math.radians(7),math.radians(14),math.radians(-8)))
    box("DEST_STORE_WALL_R",(6.6,8.9,.78),(3.8,1.0,1.38),M["soot"],.035,
        rot=(math.radians(-5),math.radians(18),math.radians(11)))
    box("DEST_PARAPET_A",(-4.3,6.7,2.85),(6.8,.42,.50),M["soot"],.025,
        rot=(math.radians(13),math.radians(-8),math.radians(5)))
    box("DEST_RED_BAND",(4.5,5.0,1.30),(5.6,.22,.45),M["char"],.018,
        rot=(math.radians(-11),math.radians(16),math.radians(-6)))

    # Blackened glass/frame remnants.
    for i,x in enumerate((-5.5,-2.4,2.1,5.3)):
        box("DEST_GLASS_"+str(i),(x,4.45,.65+i*.10),(1.0,.035,.85),M["charcoal"],.006,
            rot=(math.radians(4*i),math.radians(6-i*2),math.radians((-1)**i*8)))
        box("DEST_FRAME_"+str(i),(x+.45,4.42,.70+i*.11),(.07,.07,1.35),M["soot"],.006,
            rot=(math.radians(3*i),0,math.radians((-1)**i*12)))

    # Collapsed canopy heavily blackened around the pump zone.
    box("DEST_CANOPY_A",(-5.0,-3.8,1.55),(12.0,7.0,.52),M["soot"],.07,
        rot=(math.radians(14),math.radians(-17),math.radians(7)))
    box("DEST_CANOPY_B",(5.6,-2.7,1.15),(10.6,6.4,.52),M["char"],.07,
        rot=(math.radians(-10),math.radians(23),math.radians(-7)))
    box("DEST_RED_FASCIA_A",(-5.0,-7.1,1.12),(10.7,.24,.54),M["char"],.02,
        rot=(math.radians(11),math.radians(-16),math.radians(6)))
    box("DEST_RED_FASCIA_B",(5.7,.1,1.25),(9.4,.24,.54),M["soot"],.02,
        rot=(math.radians(-8),math.radians(20),math.radians(-5)))
    for i,(x,y,rx,rz) in enumerate([(-10,-7,19,8),(0,-7,-24,-7),(10,-7,22,5),(-10,.6,-18,10),(10,.6,20,-9)]):
        cyl("DEST_COLUMN_"+str(i),(x,y,1.55),.22,3.2,M["soot"],12,
            rot=(math.radians(rx),0,math.radians(rz)))

    # Pump wrecks with burned cabinets, exposed dark guts and charred hoses.
    for i,(x,y,rz) in enumerate([(-7.4,-3.8,12),(-2.5,-3.0,-16),(2.6,-3.8,22),(7.4,-3.0,-11)],1):
        box("DEST_PUMP_"+str(i),(x,y,.76),(1.02,.72,1.55),M["char"],.045,
            rot=(math.radians(8),math.radians(-7),math.radians(rz)))
        box("DEST_PUMP_TOP_"+str(i),(x+.12,y-.06,1.48),(1.08,.76,.28),M["soot"],.025,
            rot=(math.radians(10),math.radians(10),math.radians(rz+6)))
        box("DEST_PUMP_GUTS_"+str(i),(x-.18,y-.25,.72),(.44,.20,.70),M["charcoal"],.018,
            rot=(0,math.radians(9),math.radians(rz)))
        hose("DEST_PUMP_HOSE_"+str(i),[(x+.35,y,1.25),(x+.7,y-.4,.55),(x+.9,y-.6,.12)],M["soot"],.025)

    # Large irregular-looking scorch mats beneath likely fuel-fire zones.
    for i,(x,y,sx,sy,rz) in enumerate([
        (-6.0,-3.6,5.8,4.4,8),(-1.7,-3.2,5.2,4.0,-5),(3.4,-3.7,5.5,4.1,11),
        (7.3,-3.0,4.8,3.6,-8),(0,5.2,10.0,4.2,3)
    ]):
        box("DEST_SCORCH_"+str(i),(x,y,.045),(sx,sy,.025),M["soot"],.05,rot=(0,0,math.radians(rz)))

    # Bent, heat-blackened pylon with surviving face fragments.
    for x in (-15.55,-13.85):
        box("DEST_PRICE_FOOT_"+str(x),(x,7.8,.18),(.78,.88,.36),M["concrete"],.06)
        box("DEST_PRICE_POST_"+str(x),(x,7.8,2.45),(.22,.30,4.6),M["soot"],.025,
            rot=(0,math.radians(7),math.radians(-3)))
    box("DEST_PRICE_CABINET",(-14.15,7.8,4.65),(4.15,.42,3.0),M["soot"],.06,
        rot=(math.radians(2),math.radians(8),math.radians(-5)))
    box("DEST_PRICE_FACE",(-14.15,7.56,4.65),(3.82,.035,2.7),M["char"],.01,
        rot=(math.radians(2),math.radians(8),math.radians(-5)))

    rubble_mats=[M["soot"],M["char"],M["concrete"],M["rust"],M["charcoal"]]
    positions=[
        (-8.0,3.0,.22,2.4,.8,.34),(-5.0,1.9,.25,1.8,1.0,.30),(-2.2,3.2,.18,1.4,.7,.28),
        (1.5,2.6,.26,2.1,.8,.32),(4.8,3.4,.20,1.6,.9,.27),(7.6,2.2,.30,2.0,1.1,.35),
        (-6.3,8.9,.23,1.5,.9,.31),(-2.8,10.7,.24,1.8,.8,.34),(3.6,10.5,.22,1.3,.8,.28),
        (7.2,7.4,.20,1.6,.7,.29),(-9.0,-1.0,.19,1.3,.8,.25),(9.2,-.7,.20,1.5,.7,.27)
    ]
    for i,(x,y,z,sx,sy,sz) in enumerate(positions):
        box("DEBRIS_"+str(i),(x,y,z),(sx,sy,sz),rubble_mats[i%len(rubble_mats)],.025,
            rot=(math.radians((i*7)%24),math.radians((i*11)%30),math.radians((i*17)%40)))

    colmat=M["charcoal"]
    for name,loc,scale,rot in [
        ("COL_DEST_STORE",(-1.0,8.2,1.45),(14.5,7.0,2.9),(0,0,0)),
        ("COL_DEST_CANOPY_A",(-5.0,-3.8,1.45),(12.0,7.0,1.25),(math.radians(14),math.radians(-17),math.radians(7))),
        ("COL_DEST_CANOPY_B",(5.6,-2.7,1.10),(10.6,6.4,1.15),(math.radians(-10),math.radians(23),math.radians(-7))),
    ]:
        o=box(name,loc,scale,colmat,0,True,rot=rot)
        o.hide_render=True


def build_station(destroyed=False):
    M=mats()
    if destroyed:
        build_destroyed(M)
        print("[TPG] Built v1.2 destroyed station: structural collapse + heavy fire blackening/soot/char.")
        return

    # Forecourt and realistic site grounding
    box("FORECOURT",(0,0,.025),(38,28,.05),M["asphalt"],.012)
    box("APRON",(0,-1.0,.02),(27.5,18.3,.08),M["concrete"],.025)
    add_ground_markings(M)
    build_storefront(M, detail=True)
    build_canopy(M, detail=True)

    # FOUR actual dispenser cabinets, not two cabinets counted as four positions.
    for idx,x in enumerate((-7.5,-2.5,2.5,7.5),1):
        build_pump(x,-3.35,idx,M)

    # Convenience-store site clutter and pylon
    for x in (-9.8,9.8):
        box("BIN_"+str(x),(x,-1.0,.60),(.62,.62,1.18),M["charcoal"],.05)
        box("WIPER_"+str(x),(x,-1.0,1.42),(.52,.22,.50),M["metal"],.035)
    build_price_sign(M)
    build_misc(M, detail=True)

    # Localized livery overlays sit in front of the legacy modeled lettering.
    # USA is baked as the base visual; DCS liveries swap only these sign textures.
    from tpg_station_liveries import add_livery_overlays
    add_livery_overlays()

    # Dedicated simplified collision objects embedded in the EDM.
    colmat=M["charcoal"]
    colliders=[
        ("COL_STORE",(0,8.0,2.10),(17.4,7.4,4.2)),
        ("COL_CANOPY",(0,-3.35,5.20),(25.6,13.9,.54)),
        ("COL_SIGN",(-14.7,7.8,4.8),(4.3,.62,7.5)),
        ("COL_AIRVAC",(10.4,3.4,.95),(1.2,.9,1.9)),
    ]
    for name,loc,scale in colliders:
        o=box(name,loc,scale,colmat,0,True)
        o.hide_render=True
    for x in (-10.6,0,10.6):
        for y in (-7.9,1.25):
            o=box("COL_COLUMN_"+str(x)+"_"+str(y),(x,y,2.58),(.58,.58,5.16),colmat,0,True)
            o.hide_render=True
    for x in (-7.5,-2.5,2.5,7.5):
        o=box("COL_PUMP_"+str(x),(x,-3.35,1.34),(2.95,1.55,2.65),colmat,0,True)
        o.hide_render=True

    # Validate all four real pump cabinets and correct ground contact.
    for i in range(1,5):
        assert bpy.data.objects.get(f"P{i}_cabinet")
    assert not bpy.data.objects.get("P5_cabinet")
    for n in ("STORE","CANOPY","PRICE_CABINET","P1_cabinet","P4_cabinet"):
        assert bpy.data.objects.get(n), n
    print("[TPG] Built v1.2 ULTRA intact station: high-detail pumps/nozzles, grounded RTUs/vents, rebuilt ads and signage.")
