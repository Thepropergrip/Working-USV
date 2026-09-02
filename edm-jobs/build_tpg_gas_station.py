import os, math, random
from pathlib import Path
import bpy
import numpy as np

DESTROYED = os.environ.get("TPG_GAS_DESTROYED", "0") == "1"
workspace = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
artifact_root = workspace / "edm-artifacts"
tex_dir = artifact_root / "Textures"
tex_dir.mkdir(parents=True, exist_ok=True)

# ---------- scene helpers ----------
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

def box(name, loc, dims, material, col, bevel=0.05, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel>0:
        mod=o.modifiers.new("EdgeSoft","BEVEL")
        mod.width=bevel
        mod.segments=2
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if material: o.data.materials.append(material)
    move_to_collection(o,col)
    return o

def cyl(name, loc, radius, depth, material, col, verts=20, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name
    if material: o.data.materials.append(material)
    move_to_collection(o,col)
    return o

# ---------- PBR texture generation ----------
def _save_rgba(name, rgb, size, colorspace="sRGB"):
    arr=np.clip(rgb,0.0,1.0)
    if arr.shape[-1] == 3:
        a=np.ones((size,size,1), dtype=np.float32)
        arr=np.concatenate([arr,a],axis=2)
    img=bpy.data.images.new(name, width=size, height=size, alpha=True)
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    if colorspace != "sRGB":
        try: img.colorspace_settings.name = "Non-Color"
        except: pass
    img.file_format='PNG'
    img.filepath_raw=str(tex_dir/(name+".png"))
    img.save()
    return img

def _surface_maps(key, base, seed, profile="paint", size=1024, rough=0.65, metal=0.0):
    rng=np.random.default_rng(seed)
    yy,xx=np.mgrid[0:size,0:size].astype(np.float32)
    u=xx/max(1,size-1); v=yy/max(1,size-1)
    fine=rng.normal(0,1,(size,size)).astype(np.float32)
    coarse=rng.normal(0,1,(size//8+2,size//8+2)).astype(np.float32)
    coarse=np.kron(coarse,np.ones((8,8),dtype=np.float32))[:size,:size]
    coarse=(coarse-coarse.mean())/(coarse.std()+1e-6)
    height=np.zeros((size,size),dtype=np.float32)

    if profile=="asphalt":
        height=0.55*fine+0.35*coarse
        speck=(rng.random((size,size))>0.992).astype(np.float32)
        albedo=np.zeros((size,size,3),dtype=np.float32)
        tone=np.array(base,dtype=np.float32)[None,None,:]
        albedo=tone + (height[...,None]*0.030)
        albedo += speck[...,None]*0.10
        # faded parking/traffic grime bands
        albedo += (0.016*np.sin(u*math.pi*14))[...,None]
    elif profile=="concrete":
        height=0.32*fine+0.22*coarse
        joint=((np.mod(xx,size/2)<3)|(np.mod(yy,size/2)<3)).astype(np.float32)
        height -= joint*0.8
        albedo=np.array(base,dtype=np.float32)[None,None,:] + height[...,None]*0.045
        albedo -= joint[...,None]*0.06
    elif profile=="stucco":
        height=0.72*fine+0.10*coarse
        albedo=np.array(base,dtype=np.float32)[None,None,:] + height[...,None]*0.025
        drip=np.maximum(0,np.sin(u*35+seed)*0.5+0.5)*(v**2)*0.018
        albedo-=drip[...,None]
    elif profile=="roof":
        seams=((np.mod(xx,size/6)<2)|(np.mod(yy,size/4)<2)).astype(np.float32)
        height=0.16*fine-seams*0.45
        albedo=np.array(base,dtype=np.float32)[None,None,:] + height[...,None]*0.035
        albedo-=seams[...,None]*0.04
    elif profile=="metal":
        brushed=np.sin(v*math.pi*80)*0.35 + fine*0.16
        height=brushed
        albedo=np.array(base,dtype=np.float32)[None,None,:] + brushed[...,None]*0.018
    elif profile=="glass":
        streak=np.sin(u*math.pi*9+seed)*0.012 + np.sin(v*math.pi*5)*0.008
        height=streak+fine*0.015
        albedo=np.array(base,dtype=np.float32)[None,None,:] + streak[...,None]
        # subtle cooler upper reflection
        albedo += ((1.0-v)*0.035)[...,None]*np.array([0.45,0.75,1.0],dtype=np.float32)
    elif profile=="rubber":
        height=0.55*fine
        albedo=np.array(base,dtype=np.float32)[None,None,:] + height[...,None]*0.012
    elif profile=="screen":
        scan=np.sin(v*math.pi*size/5)*0.006
        height=fine*0.01
        albedo=np.array(base,dtype=np.float32)[None,None,:] + scan[...,None]
        # sparse greenish LCD glow flecks
        glow=(rng.random((size,size))>0.997).astype(np.float32)
        albedo += glow[...,None]*np.array([0.10,0.20,0.12],dtype=np.float32)
    elif profile=="scorched":
        blot=np.clip(0.5+0.25*coarse+0.12*fine,0,1)
        height=0.5*fine+0.4*coarse
        albedo=np.array(base,dtype=np.float32)[None,None,:]*(0.60+0.45*blot[...,None])
        soot=np.clip((np.sin(u*22+seed)+np.sin(v*17))*0.15+0.5,0,1)
        albedo*=0.62+0.38*soot[...,None]
    else:
        height=0.22*fine+0.12*coarse
        albedo=np.array(base,dtype=np.float32)[None,None,:] + height[...,None]*0.02

    albedo=np.clip(albedo,0,1)

    # Normal map from synthetic height.
    gy,gx=np.gradient(height)
    strength=0.55 if profile in ("asphalt","concrete","stucco","scorched") else 0.28
    nx=-gx*strength; ny=-gy*strength; nz=np.ones_like(nx)
    inv=1.0/np.sqrt(nx*nx+ny*ny+nz*nz+1e-8)
    normal=np.stack([(nx*inv)*0.5+0.5,(ny*inv)*0.5+0.5,(nz*inv)*0.5+0.5],axis=2)

    # DCS RoughMet texture: use physically sensible packed values.
    local_rough=np.clip(rough + 0.055*coarse + 0.035*fine,0.04,0.98)
    ao=np.clip(0.94 - np.abs(height)*0.035,0.72,1.0)
    metallic=np.full((size,size),metal,dtype=np.float32)
    roughmet=np.stack([local_rough,metallic,ao],axis=2)

    prefix=f"tpg_gas_{key.lower()}"
    return (
        _save_rgba(prefix+"_albedo", albedo, size, "sRGB"),
        _save_rgba(prefix+"_roughmet", roughmet, size, "Non-Color"),
        _save_rgba(prefix+"_normal", normal, size, "Non-Color")
    )

M={}
def edm_material(key, base, seed, profile="paint", size=1024, rough=0.65, metal=0.0):
    from materials.materials import build_material_descriptions
    from materials.material_default import DefaultMaterial
    name="TPG_GAS_"+key
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    grp=nt.nodes.new(type=DefaultMaterial.node_group_name)
    grp.post_init(build_material_descriptions()[DefaultMaterial.name])
    albedo,rmo,norm=_surface_maps(key,base,seed,profile,size,rough,metal)
    def texnode(img,label):
        n=nt.nodes.new("ShaderNodeTexImage"); n.image=img; n.label=label; return n
    a=texnode(albedo,"Albedo")
    r=texnode(rmo,"RoughMet")
    n=texnode(norm,"Normal")
    if grp.inputs.get("Base Color"): nt.links.new(a.outputs["Color"],grp.inputs["Base Color"])
    if grp.inputs.get("RoughMet (Non-Color)"): nt.links.new(r.outputs["Color"],grp.inputs["RoughMet (Non-Color)"])
    if grp.inputs.get("Normal (Non-Color)"): nt.links.new(n.outputs["Color"],grp.inputs["Normal (Non-Color)"])
    if grp.outputs: nt.links.new(grp.outputs[0],out.inputs["Surface"])
    return m

def mat(key,base,seed,profile="paint",size=1024,rough=0.65,metal=0.0):
    if key not in M:
        M[key]=edm_material(key,base,seed,profile,size,rough,metal)
    return M[key]

# ---------- materials ----------
def MAT(key):
    specs={
      "ASPHALT":((0.16,0.17,0.17),7,"asphalt",1024,0.91,0.0),
      "CONCRETE":((0.42,0.42,0.40),1,"concrete",1024,0.82,0.0),
      "STUCCO":((0.71,0.66,0.55),8,"stucco",1024,0.78,0.0),
      "ROOF":((0.11,0.12,0.125),9,"roof",1024,0.76,0.02),
      "CANOPY":((0.77,0.76,0.70),12,"metal",1024,0.48,0.18),
      "COLUMN":((0.63,0.64,0.61),13,"metal",512,0.46,0.28),
      "PUMP":((0.18,0.20,0.21),2,"metal",1024,0.38,0.28),
      "ACCENT":((0.62,0.055,0.035),4,"paint",1024,0.34,0.08),
      "SCREEN":((0.018,0.032,0.035),3,"screen",512,0.22,0.0),
      "RUBBER":((0.012,0.012,0.011),5,"rubber",512,0.86,0.0),
      "METAL":((0.18,0.19,0.18),6,"metal",512,0.30,0.72),
      "GLASS":((0.045,0.075,0.095),10,"glass",1024,0.10,0.0),
      "SIGN":((0.88,0.84,0.70),11,"paint",1024,0.28,0.03),
      "BOLLARD":((0.90,0.62,0.055),14,"paint",512,0.42,0.12),
      "HVAC":((0.42,0.44,0.43),15,"metal",512,0.56,0.45),
      "SCORCHED":((0.20,0.17,0.13),18,"scorched",1024,0.92,0.08),
      "WHITE":((0.82,0.82,0.78),21,"paint",512,0.44,0.05),
      "DARK":((0.055,0.06,0.06),22,"paint",512,0.40,0.10)
    }
    b,s,p,z,r,m=specs[key]
    return mat(key,b,s,p,z,r,m)

# ---------- detailed asset modeling ----------
def pump(x,y,col,detail):
    box(f"PumpIsland_{x}",(x,y,0.14),(2.25,1.25,0.28),MAT("CONCRETE"),col,0.09)
    box(f"PumpBody_{x}",(x,y,1.05),(0.96,0.62,1.78),MAT("PUMP"),col,0.065)
    box(f"PumpHead_{x}",(x,y,1.78),(1.02,0.66,0.34),MAT("ACCENT"),col,0.045)
    box(f"PumpScreen_{x}",(x,y-0.326,1.25),(0.63,0.035,0.38),MAT("SCREEN"),col,0.012)
    box(f"PumpKeypad_{x}",(x+0.19,y-0.347,0.91),(0.22,0.024,0.23),MAT("DARK"),col,0.008)
    box(f"PumpCard_{x}",(x-0.22,y-0.347,0.91),(0.11,0.024,0.23),MAT("DARK"),col,0.008)
    box(f"PumpLowerPanel_{x}",(x,y-0.326,0.55),(0.66,0.035,0.34),MAT("WHITE"),col,0.012)
    if detail==0:
        for sx in (-0.60,0.60):
            cyl(f"Hose_{x}_{sx}",(x+sx,y,1.02),0.028,1.26,MAT("RUBBER"),col,12)
            box(f"Nozzle_{x}_{sx}",(x+sx,y-0.10,0.69),(0.13,0.16,0.30),MAT("METAL"),col,0.025)
            box(f"HoseMount_{x}_{sx}",(x+sx,y,1.63),(0.11,0.18,0.16),MAT("DARK"),col,0.02)

def build_level(col,detail):
    box("Forecourt",(0,0,0.07),(36,27,0.14),MAT("ASPHALT"),col,0.01)
    # raised store pad and curb
    box("StorePad",(0,7.85,0.16),(20.0,8.0,0.30),MAT("CONCRETE"),col,0.05)
    box("Store",(0,8.15,2.22),(18.4,7.0,4.25),MAT("STUCCO"),col,0.07)
    box("StoreRoof",(0,8.15,4.48),(19.0,7.6,0.30),MAT("ROOF"),col,0.035)
    # parapet lip
    for yy in (4.42,11.88):
        box(f"ParapetY_{yy}",(0,yy,4.79),(19.2,0.20,0.42),MAT("DARK"),col,0.025)
    for xx in (-9.5,9.5):
        box(f"ParapetX_{xx}",(xx,8.15,4.79),(0.20,7.6,0.42),MAT("DARK"),col,0.025)

    # storefront
    box("StoreGlass",(0,4.60,2.15),(11.9,0.075,2.62),MAT("GLASS"),col,0.008)
    box("Door",(4.85,4.56,1.66),(1.40,0.095,2.92),MAT("GLASS"),col,0.008)
    box("DoorFrame",(4.85,4.50,3.12),(1.50,0.12,0.12),MAT("METAL"),col,0.01)
    box("Fascia",(0,4.47,3.93),(18.3,0.18,0.68),MAT("ACCENT"),col,0.025)
    box("StoreSignBack",(0,4.35,3.94),(7.4,0.06,0.40),MAT("DARK"),col,0.015)
    # logo bars create readable branded look without font dependency
    for i,w in enumerate((2.2,1.55,1.1)):
        box(f"LogoBar_{i}",(-2.4+i*2.0,4.31,3.94),(w,0.025,0.12),MAT("SIGN"),col,0.006)
    if detail<=1:
        for x in (-5.0,-2.5,0,2.5,5.0):
            box(f"Mullion_{x}",(x,4.51,2.15),(0.075,0.09,2.62),MAT("METAL"),col,0.006)
        # sidewalk bollards
        for x in (-8.2,-6.3,-4.4,6.3,8.2):
            cyl(f"StoreBollard_{x}",(x,4.0,0.58),0.10,1.16,MAT("BOLLARD"),col,14)

    # canopy
    box("Canopy",(0,-3.40,5.12),(23.2,11.9,0.42),MAT("CANOPY"),col,0.04)
    # fascia all sides
    box("CanopyFrontBand",(0,-9.35,5.08),(23.25,0.18,0.76),MAT("ACCENT"),col,0.018)
    box("CanopyRearBand",(0,2.55,5.08),(23.25,0.18,0.54),MAT("WHITE"),col,0.018)
    box("CanopyLeftBand",(-11.58,-3.4,5.08),(0.18,11.9,0.54),MAT("WHITE"),col,0.018)
    box("CanopyRightBand",(11.58,-3.4,5.08),(0.18,11.9,0.54),MAT("WHITE"),col,0.018)
    for x in (-9.0,9.0):
        for y in (-6.7,-0.15):
            box(f"Column_{x}_{y}",(x,y,2.57),(0.42,0.42,5.14),MAT("COLUMN"),col,0.035)
            box(f"ColumnBase_{x}_{y}",(x,y,0.17),(0.72,0.72,0.34),MAT("CONCRETE"),col,0.055)
    for x in (-7.5,-2.5,2.5,7.5):
        pump(x,-3.4,col,detail)

    # road price sign
    box("SignPole",(14.0,-5.8,3.1),(0.46,0.46,6.2),MAT("METAL"),col,0.025)
    box("RoadSign",(14.0,-5.8,6.40),(3.45,0.40,2.30),MAT("ACCENT"),col,0.045)
    box("RoadSignInset",(14.0,-6.02,6.38),(2.82,0.035,1.65),MAT("DARK"),col,0.01)
    for j in range(3):
        box(f"PriceStrip_{j}",(14.0,-6.045,6.92-j*0.54),(2.35,0.015,0.18),MAT("SIGN"),col,0.004)

    if detail<=1:
        for x in (-5.2,0,5.2):
            box(f"HVAC_{x}",(x,8.2,5.02),(2.05,1.55,0.78),MAT("HVAC"),col,0.035)
            box(f"HVACCap_{x}",(x,8.2,5.44),(1.60,1.12,0.09),MAT("DARK"),col,0.015)
    if detail==0:
        for x in (-7.5,-2.5,2.5,7.5):
            box(f"CanopyLight_{x}",(x,-3.4,4.88),(1.55,0.62,0.045),MAT("SIGN"),col,0.006)
        # wheel stops and trash bin
        for x in (-6.8,-2.3,2.3,6.8):
            box(f"WheelStop_{x}",(x,2.45,0.18),(1.65,0.24,0.22),MAT("CONCRETE"),col,0.045)
        box("TrashBin",(7.7,3.4,0.65),(0.70,0.65,1.30),MAT("DARK"),col,0.055)

def build_destroyed_level(col,detail):
    box("Forecourt",(0,0,0.07),(36,27,0.14),MAT("ASPHALT"),col,0.01)
    box("StoreRuin",(0,8.2,1.55),(18.0,6.8,3.1),MAT("SCORCHED"),col,0.055,rot=(math.radians(2),0,math.radians(-1)))
    box("RoofSlab",(-1.0,7.6,3.25),(14.5,5.4,0.34),MAT("ROOF"),col,0.03,rot=(math.radians(7),math.radians(-11),math.radians(2)))
    box("CanopyWreckA",(-5.3,-3.8,1.35),(11.0,5.3,0.42),MAT("SCORCHED"),col,0.035,rot=(math.radians(9),math.radians(-23),math.radians(12)))
    box("CanopyWreckB",(6.4,-2.8,1.0),(9.5,4.8,0.42),MAT("SCORCHED"),col,0.035,rot=(math.radians(-14),math.radians(19),math.radians(-8)))
    for i,x in enumerate((-7.5,-2.5,2.5,7.5)):
        box(f"PumpWreck_{i}",(x,-3.2,0.55),(1.0,0.62,1.45),MAT("SCORCHED"),col,0.045,rot=(math.radians(15+8*i),math.radians(8*i),math.radians((-1)**i*18)))
    if detail<=1:
        debris=[(-8,1.0,.30,2.2,1.0,.35),(-3,-6,.25,1.4,.8,.3),(3,-7,.30,2.0,1.2,.35),(8,0,.26,1.5,.9,.25),(1,4,.22,1.0,.65,.22)]
        for i,(x,y,z,dx,dy,dz) in enumerate(debris):
            box(f"Debris_{i}",(x,y,z),(dx,dy,dz),MAT("SCORCHED"),col,0.02,rot=(0,math.radians(i*7),math.radians(i*23)))

def collision_box(name,loc,dims,col):
    o=box(name,loc,dims,None,col,0.0)
    o.EDMProps.SPECIAL_TYPE='COLLISION_SHELL'
    return o

def bbox(name,loc,dims,col):
    o=box(name,loc,dims,None,col,0.0)
    o.EDMProps.SPECIAL_TYPE='BOUNDING_BOX'
    return o

clear()
root=make_col("TPG_GAS_ROOT")
lod0=make_col("TPG_GAS_LOD_0_150",root)
lod1=make_col("TPG_GAS_LOD_1_500",root)
lod2=make_col("TPG_GAS_LOD_2_2000",root)
support=make_col("TPG_GAS_SUPPORT",root)

if DESTROYED:
    build_destroyed_level(lod0,0); build_destroyed_level(lod1,1); build_destroyed_level(lod2,2)
    collision_box("COL_RUIN_STORE",(0,8.2,1.5),(18.2,7.0,3.0),support)
    collision_box("COL_WRECK_A",(-5.3,-3.8,1.0),(11.0,5.3,1.6),support)
    collision_box("COL_WRECK_B",(6.4,-2.8,0.9),(9.5,4.8,1.4),support)
    bbox("BOUNDING_BOX",(0,1.0,3.0),(36,27,7.0),support)
else:
    build_level(lod0,0); build_level(lod1,1); build_level(lod2,2)
    collision_box("COL_STORE",(0,8.15,2.22),(18.4,7.0,4.25),support)
    collision_box("COL_CANOPY",(0,-3.4,5.12),(23.2,11.9,0.42),support)
    for x in (-9.0,9.0):
        for y in (-6.7,-0.15):
            collision_box(f"COL_COLUMN_{x}_{y}",(x,y,2.57),(0.50,0.50,5.14),support)
    for x in (-7.5,-2.5,2.5,7.5):
        collision_box(f"COL_PUMP_{x}",(x,-3.4,1.05),(1.20,1.10,2.05),support)
    collision_box("COL_SIGN",(14.0,-5.8,3.6),(3.6,0.75,7.2),support)
    bbox("BOUNDING_BOX",(0,1.0,3.6),(36,27,8.2),support)

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
print("[TPG GAS HQ] variant=", "destroyed" if DESTROYED else "intact")
print("[TPG GAS HQ] objects=", len(bpy.context.scene.objects))
print("[TPG GAS HQ] textures=", len(list(tex_dir.glob("*.png"))))
