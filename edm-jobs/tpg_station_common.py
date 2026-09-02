import bpy, math, os, random
from pathlib import Path
from mathutils import Vector

WORK = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
TEXDIR = WORK / "edm-artifacts" / "Textures"
TEXDIR.mkdir(parents=True, exist_ok=True)

# Official ED material helpers are available because export_job.py enables the addon first.
from materials.materials import build_material_descriptions
from materials.material_tools import createEdmNodeGroup
from enums import NodeSocketInDefaultEnum
from objects_custom_props import get_edm_props

MAT_DESCS = build_material_descriptions()

def texture(name, base, variation=0.05, stripe=False):
    path = TEXDIR / (name + ".png")
    if path.exists():
        return path
    w=h=256
    img=bpy.data.images.new(name, width=w, height=h, alpha=True)
    rng=random.Random(hash(name) & 0xffffffff)
    px=[]
    for y in range(h):
        for x in range(w):
            n=(rng.random()-0.5)*variation
            if stripe:
                n += 0.035*math.sin((x+y)*0.18)
            r=max(0,min(1,base[0]+n)); g=max(0,min(1,base[1]+n)); b=max(0,min(1,base[2]+n))
            px.extend((r,g,b,1.0))
    img.pixels=px
    img.filepath_raw=str(path)
    img.file_format='PNG'
    img.save()
    return path

def edm_mat(name, color, rough=0.7, metal=0.0, variation=0.035, stripe=False):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    m.node_tree.nodes.clear()
    group=createEdmNodeGroup("EDM_Default_Material", m)
    group.post_init(MAT_DESCS["EDM_Default_Material"])
    group.name="Group"
    tex=m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image=bpy.data.images.load(str(texture(name, color, variation, stripe)), check_existing=True)
    m.node_tree.links.new(tex.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])
    # Rough/metal are supplied through a flat generated RMO map to keep DCS response stable.
    rmo_path=TEXDIR/(name+"_RoughMet.png")
    if not rmo_path.exists():
        img=bpy.data.images.new(name+"_RoughMet",width=8,height=8,alpha=True)
        # R=AO, G=roughness, B=metallic
        img.pixels=[1.0,rough,metal,1.0]*64
        img.filepath_raw=str(rmo_path); img.file_format='PNG'; img.save()
    rmo=m.node_tree.nodes.new("ShaderNodeTexImage")
    rmo.image=bpy.data.images.load(str(rmo_path), check_existing=True)
    rmo.image.colorspace_settings.name='Non-Color'
    m.node_tree.links.new(rmo.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    return m

MATS = {}
def mats():
    if MATS: return MATS
    MATS.update({
        "asphalt": edm_mat("TPG_Asphalt",(0.16,0.17,0.18),0.94,0.0,0.07,True),
        "concrete": edm_mat("TPG_Concrete",(0.54,0.55,0.53),0.88,0.0,0.055,True),
        "stucco": edm_mat("TPG_Stucco",(0.76,0.72,0.65),0.83,0.0,0.045,True),
        "white": edm_mat("TPG_PaintedWhite",(0.83,0.84,0.80),0.55,0.02,0.025),
        "red": edm_mat("TPG_BrandRed",(0.55,0.045,0.035),0.42,0.10,0.025),
        "charcoal": edm_mat("TPG_Charcoal",(0.09,0.10,0.11),0.54,0.05,0.03),
        "metal": edm_mat("TPG_Metal",(0.34,0.36,0.38),0.34,0.72,0.025),
        "glass": edm_mat("TPG_Glass",(0.08,0.16,0.19),0.20,0.15,0.012),
        "rubber": edm_mat("TPG_Rubber",(0.025,0.028,0.03),0.92,0.0,0.018),
        "screen": edm_mat("TPG_Screen",(0.06,0.10,0.07),0.28,0.08,0.01),
        "yellow": edm_mat("TPG_SafetyYellow",(0.72,0.48,0.025),0.63,0.02,0.03),
        "damage": edm_mat("TPG_Damage",(0.11,0.075,0.055),0.93,0.05,0.12,True),
    })
    return MATS

def box(name, loc, scale, mat, bevel=0.05, coll=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new("edge_soften","BEVEL"); mod.width=bevel; mod.segments=2
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.materials.append(mat)
    if coll:
        get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    return o

def cyl(name, loc, radius, depth, mat, verts=16, coll=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
    o=bpy.context.object; o.name=name; o.data.materials.append(mat)
    if coll: get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    return o

def text_obj(text, name, loc, size, mat, rot=(math.radians(90),0,0), extrude=.025, align='CENTER'):
    c=bpy.data.curves.new(name+"_curve",'FONT'); c.body=text; c.align_x=align
    c.size=size; c.extrude=extrude; c.bevel_depth=.006; c.bevel_resolution=1
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o)
    o.location=loc; o.rotation_euler=rot; o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o=bpy.context.object; o.name=name
    return o

def hose(name, points, mat):
    crv=bpy.data.curves.new(name+"_curve",'CURVE'); crv.dimensions='3D'; crv.bevel_depth=.035; crv.bevel_resolution=2
    spl=crv.splines.new('POLY'); spl.points.add(len(points)-1)
    for p,co in zip(spl.points,points): p.co=(co[0],co[1],co[2],1)
    o=bpy.data.objects.new(name,crv); bpy.context.collection.objects.link(o); o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.object.convert(target='MESH')
    return bpy.context.object

def build_pump(x,y,idx,M):
    box(f"P{idx}_island",(x,y,.18),(3.3,1.45,.36),M["concrete"],.12)
    box(f"P{idx}_cabinet",(x,y,1.42),(1.05,.76,2.45),M["white"],.09)
    box(f"P{idx}_top",(x,y,2.38),(1.10,.80,.32),M["red"],.06)
    for side,sy in (("A",-.395),("B",.395)):
        box(f"P{idx}_{side}_panel",(x,y+sy,1.63),(.78,.035,.58),M["charcoal"],.015)
        box(f"P{idx}_{side}_screen",(x,y+sy*1.01,1.78),(.46,.025,.19),M["screen"],.006)
        box(f"P{idx}_{side}_buttons",(x,y+sy*1.02,1.43),(.46,.025,.18),M["metal"],.006)
        # dual hose loops, readable in silhouette
        s=1 if sy>0 else -1
        hose(f"P{idx}_{side}_hose1",[(x-.44,y+sy+s*.04,2.03),(x-.72,y+sy+s*.22,1.55),(x-.58,y+sy+s*.26,.75)],M["rubber"])
        hose(f"P{idx}_{side}_hose2",[(x+.44,y+sy+s*.04,2.03),(x+.72,y+sy+s*.22,1.55),(x+.58,y+sy+s*.26,.75)],M["rubber"])
    for bx in (-1.25,1.25):
        cyl(f"P{idx}_bollard_{bx}",(x+bx,y,.65),.10,1.3,M["yellow"],12)

def build_station(destroyed=False):
    M=mats()
    # Forecourt
    box("FORECOURT",(0,0,-.08),(38,28,.16),M["asphalt"],.02)
    # lighter concrete apron breaks up the dark forecourt
    box("APRON",(0,-1.0,.02),(27,18,.08),M["concrete"],.025)
    # store
    box("STORE",(0,8.1,2.1),(17,7.2,4.2),M["stucco"],.10)
    box("STORE_PARAPET",(0,8.1,4.35),(17.4,7.55,.55),M["white"],.08)
    box("STORE_RED_BAND",(0,4.34,3.72),(17.4,.18,.55),M["red"],.02)
    # storefront glazing and frames
    for x in (-6.7,-4.5,-2.3,2.3,4.5,6.7):
        box("GLASS_"+str(x),(x,4.46,2.05),(1.75,.06,2.55),M["glass"],.015)
        # proper mullions instead of a solid frame plate
        box("FRAME_L_"+str(x),(x-.91,4.40,2.05),(.07,.06,2.68),M["charcoal"],.01)
        box("FRAME_R_"+str(x),(x+.91,4.40,2.05),(.07,.06,2.68),M["charcoal"],.01)
        box("FRAME_T_"+str(x),(x,4.40,3.36),(1.88,.06,.07),M["charcoal"],.01)
        box("FRAME_B_"+str(x),(x,4.40,.74),(1.88,.06,.07),M["charcoal"],.01)
    box("DOOR_GLASS",(0,4.43,1.75),(1.65,.07,3.15),M["glass"],.015)
    box("DOOR_L",(-.88,4.39,1.75),(.08,.06,3.35),M["charcoal"],.01)
    box("DOOR_R",(.88,4.39,1.75),(.08,.06,3.35),M["charcoal"],.01)
    box("DOOR_T",(0,4.39,3.39),(1.84,.06,.08),M["charcoal"],.01)
    box("DOOR_B",(0,4.39,.11),(1.84,.06,.08),M["charcoal"],.01)
    box("DOOR_HANDLE",(.55,4.31,1.78),(.07,.06,.72),M["metal"],.01)
    text_obj("TPG FUEL AND LUUUUBE","STORE_SIGN",(0,4.17,4.05),.58,M["red"],rot=(math.radians(90),0,0),extrude=.04)

    # canopy, generous light soffit and visible brand band
    box("CANOPY",(0,-3.2,5.15),(25,13.8,.62),M["white"],.12)
    box("CANOPY_RED_FRONT",(0,-10.0,5.20),(25.1,.22,.58),M["red"],.03)
    box("CANOPY_RED_REAR",(0,3.6,5.20),(25.1,.22,.58),M["red"],.03)
    text_obj("TPG FUEL AND LUUUUBE","CANOPY_SIGN",(0,-10.14,5.18),.64,M["white"],rot=(math.radians(90),0,0),extrude=.035)
    for x in (-10.4,10.4):
        for y in (-8.0,1.7):
            box("COLUMN_"+str(x)+"_"+str(y),(x,y,2.55),(.48,.48,5.1),M["white"],.055)
            box("COL_GUARD_"+str(x)+"_"+str(y),(x,y,.55),(1.05,1.05,1.1),M["yellow"],.08)

    # exactly TWO double-sided pumps = 4 fueling positions
    build_pump(-5.0,-3.2,1,M)
    build_pump(5.0,-3.2,2,M)

    # bins/wiper stations
    for x in (-7.7,7.7):
        box("BIN_"+str(x),(x,-1.2,.62),(.62,.62,1.22),M["charcoal"],.05)
        box("WIPER_"+str(x),(x,-1.2,1.52),(.52,.22,.62),M["metal"],.04)

    # rooftop HVAC and vents
    for x in (-5.2,0,5.2):
        box("HVAC_"+str(x),(x,8.0,4.98),(2.2,1.55,.72),M["metal"],.07)
        for i in range(4):
            box("HVAC_SLAT_"+str(x)+"_"+str(i),(x-0.7+i*.46,7.20,5.03),(.25,.03,.36),M["charcoal"],.0)
    for x in (-3.2,3.2):
        cyl("VENT_"+str(x),(x,9.6,5.2),.28,.65,M["metal"],12)

    # freestanding sign - actual geometry keeps brand/prices crisp
    box("PRICE_POLE",(-14.7,8.0,3.4),(.55,.55,6.8),M["charcoal"],.04)
    box("PRICE_BOARD",(-14.7,8.0,7.0),(4.25,.45,5.8),M["white"],.09)
    box("PRICE_HEADER",(-14.7,7.75,8.93),(4.18,.08,1.25),M["red"],.02)
    text_obj("TPG", "PRICE_TPG",(-14.7,7.67,8.85),1.0,M["white"],rot=(math.radians(90),0,0),extrude=.035)
    text_obj("FUEL + LUUUUBE","PRICE_SUB",(-14.7,7.66,8.04),.35,M["charcoal"],rot=(math.radians(90),0,0),extrude=.025)
    text_obj("REGULAR 87","PRICE_87",(-14.7,7.66,6.95),.43,M["charcoal"],rot=(math.radians(90),0,0),extrude=.025)
    text_obj("$3.95","PRICE_395",(-14.7,7.65,5.80),.88,M["red"],rot=(math.radians(90),0,0),extrude=.035)

    # Collision shells: simple, stable, invisible in DCS.
    colmat=M["charcoal"]
    for name,loc,scale in [
        ("COL_STORE",(0,8.1,2.1),(17,7.2,4.2)),
        ("COL_CANOPY",(0,-3.2,5.15),(25,13.8,.62)),
        ("COL_SIGN",(-14.7,8.0,4.5),(4.25,.55,9.0)),
    ]:
        o=box(name,loc,scale,colmat,0,True); o.hide_render=True
    for x in (-10.4,10.4):
        for y in (-8.0,1.7):
            o=box("COL_COLUMN_"+str(x)+"_"+str(y),(x,y,2.55),(.65,.65,5.1),colmat,0,True); o.hide_render=True
    for x in (-5.0,5.0):
        o=box("COL_PUMP_"+str(x),(x,-3.2,1.42),(3.4,1.55,2.6),colmat,0,True); o.hide_render=True

    if destroyed:
        # Remove intact canopy fascia/signage and create a visibly collapsed, scorched state.
        for n in ["CANOPY","CANOPY_RED_FRONT","CANOPY_RED_REAR","CANOPY_SIGN","STORE_SIGN","PRICE_HEADER","PRICE_TPG","PRICE_SUB","PRICE_87","PRICE_395"]:
            o=bpy.data.objects.get(n)
            if o: bpy.data.objects.remove(o, do_unlink=True)
        # collapsed canopy slabs
        slab=box("DEST_CANOPY_A",(-4.6,-3.6,2.3),(12.2,7.0,.55),M["damage"],.08); slab.rotation_euler=(math.radians(12),math.radians(-18),math.radians(7))
        slab=box("DEST_CANOPY_B",(5.0,-2.2,1.65),(11.2,6.2,.55),M["damage"],.08); slab.rotation_euler=(math.radians(-8),math.radians(26),math.radians(-6))
        # broken storefront and roof debris
        for i,(x,y,z,sx,sy,sz) in enumerate([
            (-5.5,3.6,.35,3.2,1.2,.35),(2.0,2.9,.28,4.0,1.5,.28),(7.5,5.0,.4,2.5,1.0,.4),
            (-1.5,7.0,4.9,5.0,2.0,.30),(5.0,8.5,4.7,3.0,2.0,.35)
        ]):
            d=box("DEBRIS_"+str(i),(x,y,z),(sx,sy,sz),M["damage"],.04)
            d.rotation_euler=(math.radians(i*7),math.radians(i*11),math.radians(i*13))
        # scorch patches
        for x,y,sx,sy in [(-5,-3,5,4),(5,-3,5,4),(0,5,8,3),(-14.7,8,4,3)]:
            box("SCORCH_"+str(x)+"_"+str(y),(x,y,.075),(sx,sy,.03),M["damage"],.0)
        # bend the roadside sign
        pole=bpy.data.objects.get("PRICE_POLE")
        board=bpy.data.objects.get("PRICE_BOARD")
        if pole: pole.rotation_euler[1]=math.radians(11)
        if board: board.rotation_euler[1]=math.radians(11)

    # scene validation
    assert bpy.data.objects.get("P1_cabinet") and bpy.data.objects.get("P2_cabinet")
    assert not bpy.data.objects.get("P3_cabinet")
    print("[TPG] Built", "destroyed" if destroyed else "intact", "TPG Fuel and Luuuube station; 2 double-sided pumps / 4 fueling positions.")
