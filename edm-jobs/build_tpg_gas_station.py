import os, math, random
from pathlib import Path
import bpy

DESTROYED = os.environ.get("TPG_GAS_DESTROYED", "0") == "1"
workspace = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
artifact_root = workspace / "edm-artifacts"
tex_dir = artifact_root / "Textures"
tex_dir.mkdir(parents=True, exist_ok=True)

# -------- helpers --------
def clear():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if c.name != "Collection":
            bpy.data.collections.remove(c)

def move_to_collection(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)

def make_col(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c

def texture(name, rgb, seed=0, grime=0.06):
    random.seed(seed)
    size = 128
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    px=[]
    for y in range(size):
        for x in range(size):
            n=(random.random()-0.5)*grime
            stripe = 0.035*math.sin((x+y*0.37)*0.19)
            r=max(0,min(1,rgb[0]+n+stripe))
            g=max(0,min(1,rgb[1]+n+stripe))
            b=max(0,min(1,rgb[2]+n+stripe))
            px += [r,g,b,1.0]
    img.pixels = px
    img.file_format='PNG'
    img.filepath_raw=str(tex_dir/(name+".png"))
    img.save()
    return img

def edm_material(name, rgb, seed=0, grime=0.05):
    from materials.materials import build_material_descriptions
    from materials.material_default import DefaultMaterial
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    nt=m.node_tree
    nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    grp=nt.nodes.new(type=DefaultMaterial.node_group_name)
    grp.post_init(build_material_descriptions()[DefaultMaterial.name])
    tex=nt.nodes.new("ShaderNodeTexImage")
    tex.image=texture(name+"_ALBEDO", rgb, seed, grime)
    base=grp.inputs.get("Base Color")
    if base:
        nt.links.new(tex.outputs["Color"], base)
    if grp.outputs:
        nt.links.new(grp.outputs[0], out.inputs["Surface"])
    return m

M = {}
def mat(key,rgb,seed,grime=0.05):
    if key not in M: M[key]=edm_material("TPG_GAS_"+key,rgb,seed,grime)
    return M[key]

def box(name, loc, dims, material, col, bevel=0.06, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel>0:
        mod=o.modifiers.new("EdgeSoft","BEVEL"); mod.width=bevel; mod.segments=2
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if material: o.data.materials.append(material)
    move_to_collection(o,col)
    return o

def cyl(name, loc, radius, depth, material, col, verts=16, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name
    if material: o.data.materials.append(material)
    move_to_collection(o,col)
    return o

def sign_panel(name, loc, dims, material, col, rot=(0,0,0)):
    return box(name,loc,dims,material,col,0.02,rot)

def pump(x, y, col, detail):
    island=box(f"PumpIsland_{x}",(x,y,0.13),(2.15,1.15,0.26),mat("CONCRETE",(0.38,0.39,0.39),1,0.09),col,0.08)
    p=box(f"Pump_{x}",(x,y,1.05),(1.02,0.58,1.84),mat("PUMP",(0.16,0.18,0.19),2,0.07),col,0.08)
    sign_panel(f"PumpFace_{x}",(x,y-0.303,1.18),(0.74,0.035,0.54),mat("SCREEN",(0.035,0.05,0.06),3,0.01),col)
    sign_panel(f"PumpBrand_{x}",(x,y-0.323,1.67),(0.82,0.025,0.19),mat("ACCENT",(0.68,0.10,0.055),4,0.03),col)
    if detail==0:
        # hose columns + nozzle blocks
        for sx in (-0.62,0.62):
            cyl(f"Hose_{x}_{sx}",(x+sx,y,1.03),0.035,1.25,mat("RUBBER",(0.02,0.02,0.018),5,0.02),col,10)
            box(f"Nozzle_{x}_{sx}",(x+sx,y-0.09,0.68),(0.14,0.18,0.32),mat("METAL",(0.13,0.13,0.12),6,0.03),col,0.025)

def build_level(col, detail):
    # ground/forecourt
    box("Forecourt",(0,0,0.07),(36,27,0.14),mat("ASPHALT",(0.18,0.19,0.19),7,0.12),col,0.02)
    # store shell
    box("Store",(0,8.0,2.15),(18.5,7.2,4.3),mat("STUCCO",(0.73,0.69,0.58),8,0.06),col,0.08)
    box("StoreRoof",(0,8.0,4.48),(19.0,7.7,0.38),mat("ROOF",(0.16,0.17,0.17),9,0.08),col,0.04)
    # storefront glazing / door / fascia
    box("StoreGlass",(0,4.37,2.05),(11.8,0.08,2.55),mat("GLASS",(0.07,0.105,0.12),10,0.01),col,0.01)
    box("Door",(4.7,4.31,1.55),(1.35,0.10,2.8),mat("GLASS",(0.07,0.105,0.12),10,0.01),col,0.01)
    box("Fascia",(0,4.20,3.78),(18.4,0.20,0.72),mat("ACCENT",(0.68,0.10,0.055),4,0.03),col,0.03)
    sign_panel("StoreSign",(0,4.07,3.82),(7.0,0.05,0.34),mat("SIGN",(0.92,0.88,0.72),11,0.025),col)
    # canopy
    box("Canopy",(0,-3.4,5.15),(23.0,11.8,0.52),mat("CANOPY",(0.76,0.75,0.69),12,0.045),col,0.05)
    box("CanopyBand",(0,-9.28,5.15),(23.0,0.20,0.72),mat("ACCENT",(0.68,0.10,0.055),4,0.03),col,0.02)
    for x in (-9.0,9.0):
        for y in (-6.7,-0.1):
            box(f"Column_{x}_{y}",(x,y,2.56),(0.46,0.46,5.12),mat("COLUMN",(0.68,0.68,0.64),13,0.05),col,0.04)
    # four pumps
    for x in (-7.5,-2.5,2.5,7.5): pump(x,-3.4,col,detail)
    # pylon sign
    box("SignPole",(14.0,-5.8,3.0),(0.55,0.55,6.0),mat("METAL",(0.13,0.13,0.12),6,0.03),col,0.03)
    box("RoadSign",(14.0,-5.8,6.25),(3.4,0.42,2.2),mat("ACCENT",(0.68,0.10,0.055),4,0.03),col,0.05)
    box("PricePanel",(14.0,-6.03,5.95),(2.65,0.04,0.92),mat("SCREEN",(0.035,0.05,0.06),3,0.01),col,0.01)
    if detail<=1:
        # curb / bollards
        for x in (-8.5,-6.5,-3.5,-1.5,1.5,3.5,6.5,8.5):
            cyl(f"Bollard_{x}",(x,3.9,0.56),0.11,1.12,mat("BOLLARD",(0.85,0.65,0.08),14,0.04),col,12)
        # rooftop HVAC
        for x in (-5.0,0.0,5.0):
            box(f"HVAC_{x}",(x,8.1,4.98),(2.0,1.5,0.75),mat("HVAC",(0.42,0.44,0.43),15,0.07),col,0.04)
    if detail==0:
        # canopy light panels, wheel stops and window mullions
        for x in (-7.5,-2.5,2.5,7.5):
            box(f"Light_{x}",(x,-3.4,4.86),(1.65,0.55,0.05),mat("SIGN",(0.92,0.88,0.72),11,0.025),col,0.01)
        for x in (-4.5,-1.5,1.5,4.5):
            box(f"Mullion_{x}",(x,4.25,2.05),(0.09,0.10,2.55),mat("METAL",(0.13,0.13,0.12),6,0.03),col,0.01)

def build_destroyed_level(col, detail):
    box("Forecourt",(0,0,0.07),(36,27,0.14),mat("ASPHALT",(0.15,0.15,0.145),17,0.14),col,0.02)
    # damaged store remains
    box("StoreRuin",(0,8.2,1.55),(18.0,6.8,3.1),mat("SCORCHED",(0.20,0.18,0.15),18,0.14),col,0.06,rot=(math.radians(2),0,math.radians(-1)))
    box("RoofSlab",(-1.0,7.6,3.25),(14.5,5.4,0.34),mat("ROOF",(0.12,0.12,0.115),19,0.12),col,0.03,rot=(math.radians(7),math.radians(-11),math.radians(2)))
    # collapsed canopy chunks
    box("CanopyWreckA",(-5.3,-3.8,1.35),(11.0,5.3,0.42),mat("SCORCHED",(0.20,0.18,0.15),18,0.14),col,0.04,rot=(math.radians(9),math.radians(-23),math.radians(12)))
    box("CanopyWreckB",(6.4,-2.8,1.0),(9.5,4.8,0.42),mat("SCORCHED",(0.20,0.18,0.15),18,0.14),col,0.04,rot=(math.radians(-14),math.radians(19),math.radians(-8)))
    for i,x in enumerate((-7.5,-2.5,2.5,7.5)):
        box(f"PumpWreck_{i}",(x,-3.2,0.55),(1.0,0.62,1.45),mat("SCORCHED",(0.17,0.16,0.14),20+i,0.16),col,0.05,rot=(math.radians(15+8*i),math.radians(8*i),math.radians((-1)**i*18)))
    # debris
    if detail<=1:
        debris=[(-8,1.0,.30,2.2,1.0,.35),(-3,-6,.25,1.4,.8,.3),(3,-7,.30,2.0,1.2,.35),(8,0,.26,1.5,.9,.25),(1,4,.22,1.0,.65,.22)]
        for i,(x,y,z,dx,dy,dz) in enumerate(debris):
            box(f"Debris_{i}",(x,y,z),(dx,dy,dz),mat("SCORCHED",(0.20,0.18,0.15),18,0.14),col,0.02,rot=(0,math.radians(i*7),math.radians(i*23)))

def collision_box(name, loc, dims, col):
    o=box(name,loc,dims,None,col,0.0)
    o.EDMProps.SPECIAL_TYPE='COLLISION_SHELL'
    return o

def bbox(name, loc, dims, col):
    o=box(name,loc,dims,None,col,0.0)
    o.EDMProps.SPECIAL_TYPE='BOUNDING_BOX'
    return o

clear()
root=make_col("TPG_GAS_ROOT")
# Native EDM LOD convention: *_LOD_<id>_<distance>
lod0=make_col("TPG_GAS_LOD_0_140",root)
lod1=make_col("TPG_GAS_LOD_1_450",root)
lod2=make_col("TPG_GAS_LOD_2_1800",root)
support=make_col("TPG_GAS_SUPPORT",root)

if DESTROYED:
    build_destroyed_level(lod0,0); build_destroyed_level(lod1,1); build_destroyed_level(lod2,2)
    collision_box("COL_RUIN_STORE",(0,8.2,1.5),(18.2,7.0,3.0),support)
    collision_box("COL_WRECK_A",(-5.3,-3.8,1.0),(11.0,5.3,1.6),support)
    collision_box("COL_WRECK_B",(6.4,-2.8,0.9),(9.5,4.8,1.4),support)
    bbox("BOUNDING_BOX",(0,1.0,3.0),(36,27,7.0),support)
else:
    build_level(lod0,0); build_level(lod1,1); build_level(lod2,2)
    collision_box("COL_STORE",(0,8.0,2.15),(18.5,7.2,4.3),support)
    collision_box("COL_CANOPY",(0,-3.4,5.15),(23.0,11.8,0.52),support)
    for x in (-9.0,9.0):
        for y in (-6.7,-0.1):
            collision_box(f"COL_COLUMN_{x}_{y}",(x,y,2.56),(0.46,0.46,5.12),support)
    for x in (-7.5,-2.5,2.5,7.5):
        collision_box(f"COL_PUMP_{x}",(x,-3.4,1.05),(1.2,1.1,2.0),support)
    collision_box("COL_SIGN",(14.0,-5.8,3.5),(3.5,0.7,7.0),support)
    bbox("BOUNDING_BOX",(0,1.0,3.5),(36,27,8.0),support)

# ensure sane transforms and UVs
for o in bpy.context.scene.objects:
    if o.type=='MESH':
        if len(o.data.uv_layers)==0 and o.EDMProps.SPECIAL_TYPE=='UNKNOWN_TYPE':
            o.data.uv_layers.new(name='UVMap')
        if o.EDMProps.SPECIAL_TYPE=='UNKNOWN_TYPE':
            o.EDMProps.DAMAGE_ARG=70

bpy.context.scene.frame_start=0
bpy.context.scene.frame_end=200
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
print("[TPG GAS] variant=", "destroyed" if DESTROYED else "intact")
print("[TPG GAS] objects=", len(bpy.context.scene.objects))
print("[TPG GAS] textures=", len(list(tex_dir.glob("*.png"))))
