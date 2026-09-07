import bpy, math, os, random, zipfile, shutil
from pathlib import Path
from mathutils import Vector

WS = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
ART = WS / "edm-artifacts"
MOD = ART / "TPG_Gas_Station_V1_1_1"
SHAPES = MOD / "Shapes"
TEX = MOD / "Textures"
DB = MOD / "Database"
for p in (ART, MOD, SHAPES, TEX, DB):
    p.mkdir(parents=True, exist_ok=True)

BASE = "TPG_Gas_Station_V1_1_1"

def clear():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for d in (bpy.data.materials,):
        pass

def make_tex(name, rgb, speck=0.04, size=128):
    path = TEX / f"{name}.png"
    img = bpy.data.images.get(name) or bpy.data.images.new(name, size, size)
    rng = random.Random(hash(name) & 0xffffffff)
    pix = [0.0] * (size*size*4)
    for i in range(size*size):
        n = (rng.random()-0.5)*speck
        for c in range(3):
            pix[i*4+c] = min(1.0,max(0.0,rgb[c]+n))
        pix[i*4+3] = 1.0
    img.pixels = pix
    img.filepath_raw = str(path)
    img.file_format = 'PNG'
    img.save()
    return img

TEXS = {}
def mat(name, rgb, rough=.55, metallic=0.0, textured=True):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb,1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if textured:
        img = TEXS.get(name) or make_tex(name, rgb)
        TEXS[name] = img
        node = m.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = img
        node.interpolation = 'Linear'
        m.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    return m

M_ASPH = mat("TPG_GS111_Asphalt",(0.045,0.05,0.055),.92)
M_CONC = mat("TPG_GS111_Concrete",(0.42,0.43,0.42),.82)
M_WHITE = mat("TPG_GS111_White",(0.77,0.79,0.78),.45)
M_RED = mat("TPG_GS111_Red",(0.48,0.035,0.025),.42)
M_DARK = mat("TPG_GS111_Dark",(0.045,0.055,0.065),.5)
M_GLASS = mat("TPG_GS111_Glass",(0.055,0.10,0.13),.2,0.0)
M_METAL = mat("TPG_GS111_Metal",(0.26,0.28,0.29),.33,.55)
M_YEL = mat("TPG_GS111_Yellow",(0.85,0.55,0.03),.48)
M_CHAR = mat("TPG_GS111_Char",(0.025,0.022,0.02),.96)
M_RUBBLE = mat("TPG_GS111_Rubble",(0.22,0.19,0.16),.9)

def box(name, loc, scale, material, bevel=0.0, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel>0:
        be=o.modifiers.new("edge_soften","BEVEL"); be.width=bevel; be.segments=2
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=be.name)
    o.data.materials.append(material)
    return o

def cyl(name, loc, radius, depth, material, verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
    o=bpy.context.object; o.name=name; o.data.materials.append(material); return o

def build_intact(detail=0):
    clear()
    # HOTFIX: true 5 cm asphalt slab. Bottom touches origin; top is +0.05 m.
    # This eliminates terrain coplanarity/z-fighting while keeping the forecourt nearly flush.
    box("PAVEMENT_HOTFIX",(0,0,0.025),(38,30,0.05),M_ASPH,0.015)
    # shallow concrete apron/curb zones
    box("STORE_PAD",(0,8.0,0.075),(27,9.5,0.10),M_CONC,0.025)
    # store
    box("STORE_BODY",(0,9.0,2.05),(24,7.2,4.0),M_WHITE,0.12)
    box("STORE_FASCIA",(0,5.38,3.48),(24.3,0.28,0.75),M_RED,0.04)
    box("STORE_ROOF",(0,9.0,4.18),(24.6,7.8,0.28),M_DARK,0.04)
    # storefront glazing and entrance
    for x in (-8.4,-5.2,-2.0,3.0,6.2,9.4):
        box(f"WINDOW_{x}",(x,5.34,2.05),(2.65,0.10,2.15),M_GLASS,0.025)
    box("DOOR",(0.55,5.30,1.55),(1.65,0.12,2.95),M_GLASS,0.02)
    box("DOOR_FRAME",(0.55,5.23,3.05),(1.9,0.10,0.12),M_METAL,0.01)
    # canopy
    box("CANOPY_ROOF",(0,-3.2,4.55),(28,10.0,0.50),M_WHITE,0.10)
    box("CANOPY_RED_BAND",(0,-8.13,4.54),(28.2,0.22,0.62),M_RED,0.03)
    for x,y in [(-11,-6.0),(-11,-0.4),(11,-6.0),(11,-0.4)]:
        box(f"CANOPY_COL_{x}_{y}",(x,y,2.25),(0.55,0.55,4.5),M_WHITE,0.05)
        box(f"COL_GUARD_{x}_{y}",(x,y,0.55),(0.9,0.9,1.1),M_YEL,0.08)
    # four pump islands / four dispensers
    for i,x in enumerate((-9,-3,3,9),1):
        box(f"ISLAND_{i}",(x,-3.2,0.14),(2.2,5.2,0.18),M_CONC,0.18)
        box(f"PUMP_{i}",(x,-3.2,1.18),(1.00,0.75,2.05),M_WHITE,0.08)
        box(f"PUMP_TOP_{i}",(x,-3.2,2.18),(1.04,0.80,0.18),M_RED,0.04)
        # flat decal-style pump face plates, no raised text geometry
        box(f"SCREEN_{i}",(x,-3.586,1.52),(0.58,0.025,0.38),M_DARK,0.005)
        box(f"LABEL_GREEN_{i}",(x-0.20,-3.602,1.08),(0.18,0.018,0.15),mat("TPG_GS111_LabelGreen",(0.05,0.34,0.12),.55),0)
        box(f"LABEL_BLUE_{i}",(x,-3.602,1.08),(0.18,0.018,0.15),mat("TPG_GS111_LabelBlue",(0.03,0.16,0.45),.55),0)
        box(f"LABEL_ORANGE_{i}",(x+0.20,-3.602,1.08),(0.18,0.018,0.15),mat("TPG_GS111_LabelOrange",(0.75,0.24,0.025),.55),0)
        # hoses as dark slim cylinders
        cyl(f"HOSEPOST_{i}",(x+0.46,-3.2,1.15),0.035,1.35,M_DARK,10)
        box(f"BOLLARD_L_{i}",(x-0.72,-4.95,0.55),(0.16,0.16,1.1),M_YEL,0.04)
        box(f"BOLLARD_R_{i}",(x+0.72,-4.95,0.55),(0.16,0.16,1.1),M_YEL,0.04)
    if detail < 2:
        # price monument and roof HVAC
        box("PRICE_SIGN_POST",(15.5,8.2,2.2),(0.7,0.7,4.4),M_DARK,0.05)
        box("PRICE_SIGN",(15.5,8.2,5.2),(3.2,0.45,2.2),M_RED,0.08)
        for x in (-6,0,6):
            box(f"HVAC_{x}",(x,9.0,4.72),(2.2,1.4,0.78),M_METAL,0.08)
    if detail == 0:
        # parking stripes and wheel stops are raised a few mm from asphalt to prevent their own z-fighting
        for x in (-10,-7,-4,4,7,10):
            box(f"STRIPE_{x}",(x,13.1,0.056),(0.10,3.4,0.012),M_WHITE,0)
            box(f"STOP_{x}",(x,11.8,0.13),(1.7,0.22,0.18),M_CONC,0.04)

def build_destroyed():
    clear()
    box("PAVEMENT_DEST",(0,0,0.025),(38,30,0.05),M_ASPH,0.015)
    box("STORE_PAD_DEST",(0,8,0.075),(27,9.5,0.10),M_CONC,0.025)
    box("STORE_BROKEN",(0,9.4,1.25),(24,6.4,2.35),M_CHAR,0.06)
    # collapsed canopy slabs
    box("CANOPY_COLLAPSE_A",(-5,-3.0,0.85),(14,6.5,0.38),M_CHAR,0.06,rot=(0.10,0.16,-0.06))
    box("CANOPY_COLLAPSE_B",(7,-4.0,0.62),(10,5.5,0.32),M_RUBBLE,0.05,rot=(-0.08,-0.22,0.10))
    for i,x in enumerate((-9,-3,3,9),1):
        box(f"PUMP_WRECK_{i}",(x,-3.2,0.52),(0.8,0.75,0.9),M_CHAR,0.06,rot=(0.0,(i-2.5)*0.08,0.08*i))
    rng=random.Random(111)
    for i in range(36):
        x=rng.uniform(-13,13); y=rng.uniform(-7,12); z=rng.uniform(.10,.45)
        s=rng.uniform(.15,.65)
        box(f"RUBBLE_{i}",(x,y,z),(s,rng.uniform(.12,.55),rng.uniform(.10,.45)),M_RUBBLE,0.02,rot=(rng.uniform(-.4,.4),rng.uniform(-.4,.4),rng.uniform(-3.14,3.14)))

def build_collision():
    clear()
    # collision pavement intentionally omitted: vehicles should not bump over the visual 5 cm slab
    parts=[
      ("COL_STORE",(0,9.0,2.05),(24,7.2,4.0)),
      ("COL_CANOPY",(0,-3.2,4.55),(28,10,0.50)),
    ]
    for x,y in [(-11,-6.0),(-11,-0.4),(11,-6.0),(11,-0.4)]:
        parts.append((f"COL_POST_{x}_{y}",(x,y,2.25),(0.55,0.55,4.5)))
    for i,x in enumerate((-9,-3,3,9),1):
        parts.append((f"COL_PUMP_{i}",(x,-3.2,1.18),(1.0,0.75,2.05)))
    for n,l,s in parts:
        o=box(n,l,s,M_DARK,0)
        try: o.EDMProps.SPECIAL_TYPE='COLLISION_SHELL'
        except Exception as e: print("[GS111] collision prop warning",n,e)

def write_edm(name):
    from io_scene_edm import collection_walker
    from logger import log
    path=SHAPES/name
    log.errors=[]; log.warnings=[]
    collection_walker._write(bpy.context,str(path))
    if log.errors: raise RuntimeError("EDM export errors: "+" | ".join(map(str,log.errors)))
    if not path.exists() or path.stat().st_size<1: raise RuntimeError(f"Missing EDM {path}")
    print("[GS111] wrote",path,path.stat().st_size)

# Build/export each state
build_intact(0); write_edm(BASE+".edm")
build_intact(1); write_edm(BASE+"_LOD1.edm")
build_intact(2); write_edm(BASE+"_LOD2.edm")
build_destroyed(); write_edm(BASE+"_Destroyed.edm")
build_collision(); write_edm(BASE+"_Collision.edm")
# Restore main model so outer export_job.py writes the main EDM once more
build_intact(0)

(SHAPES/(BASE+".lods")).write_text("""model={
    lods={
        {\"TPG_Gas_Station_V1_1_1.edm\",1200.0};
        {\"TPG_Gas_Station_V1_1_1_LOD1.edm\",3500.0};
        {\"TPG_Gas_Station_V1_1_1_LOD2.edm\",18000.0};
    };
    collision_shell=\"TPG_Gas_Station_V1_1_1_Collision.edm\";
}
""",encoding="utf-8")

(MOD/"entry.lua").write_text("""declare_plugin(\"TPG Gas Station V1.1.1\",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _(\"TPG Gas Station V1.1.1\"),
    version = \"1.1.1\",
    state = \"installed\",
    info = _(\"Four-dispenser roadside gas station static structure - pavement hotfix\")
})
mount_vfs_model_path(current_mod_path..\"/Shapes\")
mount_vfs_texture_path(current_mod_path..\"/Textures\")
dofile(current_mod_path..\"/Database/db_tpg_gas_station.lua\")
plugin_done()
""",encoding="utf-8")

(DB/"db_tpg_gas_station.lua").write_text("""local function add_structure(f)
    f.shape_table_data = {
        {
            file = f.ShapeName,
            life = f.Life,
            username = f.Name,
            desrt = f.ShapeNameDestr or \"self\",
            classname = \"lLandVehicle\",
            positioning = \"BYNORMAL\",
        }
    }
    if f.ShapeNameDestr then
        f.shape_table_data[#f.shape_table_data + 1] = {
            name = f.ShapeNameDestr,
            file = f.ShapeNameDestr,
        }
    end
    f.mapclasskey = \"P0091000076\"
    f.attribute = {wsType_Static, wsType_Standing, \"Structures\"}
    add_surface_unit(f)
end

add_structure({
    Name = \"TPG_Gas_Station_V1_1_1\",
    DisplayName = _(\"TPG Gas Station V1.1.1\"),
    ShapeName = \"TPG_Gas_Station_V1_1_1\",
    ShapeNameDestr = \"TPG_Gas_Station_V1_1_1_Destroyed\",
    Life = 420,
    Rate = 100,
    category = \"Structures\",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
""",encoding="utf-8")

(MOD/"README.txt").write_text("""TPG Gas Station V1.1.1
======================
DCS World Mods/tech static structure.

Install:
Copy the single folder TPG_Gas_Station_V1_1_1 directly into:
Saved Games\\DCS\\Mods\\tech\\

Mission Editor:
Static Objects > Structures > TPG Gas Station V1.1.1

Hotfix:
- asphalt forecourt rebuilt as a true 5 cm slab with top at +0.05 m
- no pavement collision bump
- raised parking markings
- LOD0/LOD1/LOD2 and destroyed state use the corrected ground treatment
- separate collision EDM retained
- unique V1.1.1 namespaces so prior versions can coexist
""",encoding="utf-8")

# clean single-folder drop-in ZIP
zip_path=ART/(BASE+"_DCS_DropIn_READY.zip")
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
    for p in MOD.rglob("*"):
        if p.is_file():
            z.write(p,arcname=str(Path(MOD.name)/p.relative_to(MOD)))
print("[GS111] ZIP",zip_path,zip_path.stat().st_size)
