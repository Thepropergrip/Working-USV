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

def _tex(name, base, variation=0.03, streak=False, soot=False, size=512):
    path = TEXDIR / (name + ".png")
    if path.exists():
        return path
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    rng = random.Random(zlib.crc32(name.encode("utf-8")) & 0xffffffff)
    stains = []
    if soot:
        for _ in range(18):
            stains.append((rng.random(), rng.random(), rng.uniform(.04,.22), rng.uniform(.04,.18), rng.uniform(.35,.82)))
    px=[]
    for y in range(size):
        for x in range(size):
            n=(rng.random()-.5)*variation
            if streak:
                n += .012*math.sin(y*.14) + .008*math.sin(x*.07+y*.03)
            dark=0.0
            if soot:
                u=x/max(1,size-1); v=y/max(1,size-1)
                for cx,cy,rx,ry,p in stains:
                    dx=(u-cx)/rx; dy=(v-cy)/ry
                    d=dx*dx+dy*dy
                    if d<1.0: dark=max(dark,p*(1.0-d)**2)
                if rng.random()>.992: dark=max(dark,rng.uniform(.12,.44))
            px.extend((
                max(0,min(1,(base[0]+n)*(1-dark))),
                max(0,min(1,(base[1]+n)*(1-dark))),
                max(0,min(1,(base[2]+n)*(1-dark))),
                1.0))
    img.pixels=px
    img.filepath_raw=str(path); img.file_format="PNG"; img.save()
    return path

def edm_mat(name,color,rough=.7,metal=0.0,variation=.03,streak=False,soot=False):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.node_tree.nodes.clear()
    group=createEdmNodeGroup("EDM_Default_Material",m)
    group.post_init(MAT_DESCS["EDM_Default_Material"]); group.name="Group"
    tex=m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image=bpy.data.images.load(str(_tex(name,color,variation,streak,soot)),check_existing=True)
    m.node_tree.links.new(tex.outputs["Color"],group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])
    rmo_path=TEXDIR/(name+"_RoughMet.png")
    if not rmo_path.exists():
        img=bpy.data.images.new(name+"_RoughMet",width=8,height=8,alpha=True)
        img.pixels=[1.0,rough,metal,1.0]*64
        img.filepath_raw=str(rmo_path); img.file_format="PNG"; img.save()
    rmo=m.node_tree.nodes.new("ShaderNodeTexImage")
    rmo.image=bpy.data.images.load(str(rmo_path),check_existing=True)
    rmo.image.colorspace_settings.name="Non-Color"
    m.node_tree.links.new(rmo.outputs["Color"],group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    return m

def mats():
    if MATS: return MATS
    MATS.update({
        "gravel":edm_mat("TPG_SUB100_Gravel",(0.34,.33,.30),.98,0,.09,True),
        "concrete":edm_mat("TPG_SUB100_Concrete",(.48,.47,.44),.92,0,.055,True),
        "brick":edm_mat("TPG_SUB100_UtilityBrick",(.31,.285,.255),.90,0,.060,True),
        "brick_mortar":edm_mat("TPG_SUB100_BrickMortar",(.54,.53,.50),.95,0,.035,True),
        "beige":edm_mat("TPG_SUB100_ServiceBeige",(.62,.60,.53),.76,.02,.030,True),
        "glass":edm_mat("TPG_SUB100_WindowGlass",(.055,.085,.095),.18,.08,.012),
        "galv":edm_mat("TPG_SUB100_Galvanized",(.48,.50,.51),.35,.78,.035,True),
        "steel":edm_mat("TPG_SUB100_Steel",(.24,.26,.27),.42,.72,.026,True),
        "xfmr":edm_mat("TPG_SUB100_TransformerGray",(.37,.42,.42),.56,.26,.028,True),
        "xfmr_dark":edm_mat("TPG_SUB100_TransformerDark",(.21,.24,.24),.68,.24,.035,True),
        "porcelain":edm_mat("TPG_SUB100_Porcelain",(.70,.73,.69),.25,.02,.018),
        "brown_porcelain":edm_mat("TPG_SUB100_BrownPorcelain",(.28,.12,.055),.31,.02,.020),
        "polymer":edm_mat("TPG_SUB100_Polymer",(.22,.24,.23),.62,.02,.020),
        "copper":edm_mat("TPG_SUB100_Copper",(.34,.16,.055),.36,.72,.025),
        "alum":edm_mat("TPG_SUB100_Aluminum",(.60,.61,.60),.28,.88,.018),
        "black":edm_mat("TPG_SUB100_Black",(.018,.020,.020),.90,.02,.018),
        "yellow":edm_mat("TPG_SUB100_SafetyYellow",(.72,.51,.035),.58,.02,.020),
        "red":edm_mat("TPG_SUB100_SafetyRed",(.54,.035,.025),.54,.02,.018),
        "blue":edm_mat("TPG_SUB100_LabelBlue",(.035,.19,.42),.50,.01,.015),
        "white":edm_mat("TPG_SUB100_LabelWhite",(.82,.82,.78),.52,.01,.012),
        "green":edm_mat("TPG_SUB100_UtilityGreen",(.10,.23,.12),.70,.02,.025,True),
        "roof":edm_mat("TPG_SUB100_Roof",(.20,.21,.20),.84,.06,.035,True),
        "soot":edm_mat("TPG_SUB100_Soot",(.015,.012,.010),.96,.01,.085,True,True),
        "burnt":edm_mat("TPG_SUB100_BurntSteel",(.085,.060,.045),.86,.14,.080,True,True),
        "oil":edm_mat("TPG_SUB100_OilStain",(.045,.038,.028),.64,.02,.055,True),
    })
    return MATS

def box(name,loc,scale,mat,bevel=.04,rot=(0,0,0),coll=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new("edge_soften","BEVEL"); mod.width=bevel; mod.segments=2
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    if mat: o.data.materials.append(mat)
    if coll: get_edm_props(o).SPECIAL_TYPE="COLLISION_SHELL"
    return o

def cyl(name,loc,radius,depth,mat,verts=16,rot=(0,0,0),coll=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name
    if mat: o.data.materials.append(mat)
    if coll: get_edm_props(o).SPECIAL_TYPE="COLLISION_SHELL"
    return o

def sphere(name,loc,r,mat,seg=16,rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,radius=r,location=loc)
    o=bpy.context.object; o.name=name
    if mat:o.data.materials.append(mat)
    return o

def torus(name,loc,major,minor,mat,rot=(0,0,0),major_segments=20,minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=major_segments,
        minor_segments=minor_segments,location=loc,rotation=rot)
    o=bpy.context.object;o.name=name
    if mat:o.data.materials.append(mat)
    return o

def text_obj(text,name,loc,size,mat,rot=(math.radians(90),0,0),extrude=.008,align="CENTER"):
    c=bpy.data.curves.new(name+"_curve","FONT"); c.body=text; c.align_x=align; c.align_y="CENTER"
    c.size=size; c.extrude=extrude; c.bevel_depth=.002; c.bevel_resolution=1
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o)
    o.location=loc; o.rotation_euler=rot; o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.object.convert(target="MESH")
    bpy.context.object.name=name
    return bpy.context.object

def cable(name,pts,mat,radius=.022,res=1):
    c=bpy.data.curves.new(name+"_curve","CURVE"); c.dimensions="3D"; c.bevel_depth=radius; c.bevel_resolution=res
    s=c.splines.new("BEZIER"); s.bezier_points.add(len(pts)-1)
    for bp,p in zip(s.bezier_points,pts):
        bp.co=p; bp.handle_left_type="AUTO"; bp.handle_right_type="AUTO"
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o); o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.object.convert(target="MESH")
    return bpy.context.object

def bolt_ring(prefix,center,radius,z,count,mat,bolt_r=.035,bolt_h=.045):
    for i in range(count):
        a=2*math.pi*i/count
        cyl(f"{prefix}_{i}",(center[0]+math.cos(a)*radius,center[1]+math.sin(a)*radius,z),
            bolt_r,bolt_h,mat,8)

def insulator_stack(name,loc,height,M,detail=2,brown=False):
    # One revolved mesh per insulator stack instead of dozens of child objects.
    # Keeps real skirt silhouette at close range while dramatically reducing EDM scene-node count.
    mat=M["brown_porcelain"] if brown else M["porcelain"]
    discs=10 if detail>=2 else (6 if detail==1 else 3)
    seg=16 if detail>=2 else (12 if detail==1 else 8)
    z0=loc[2]-height/2
    step=height/discs
    profile=[]
    for i in range(discs):
        base=z0+i*step
        # stacked shed profile: narrow neck -> shoulder -> wide porcelain skirt -> underside -> neck
        profile.extend([
            (base+.02*step,.070),
            (base+.16*step,.085),
            (base+.32*step,.145),
            (base+.47*step,.175 if detail>=2 else .155),
            (base+.58*step,.130),
            (base+.72*step,.085),
            (base+.96*step,.070),
        ])
    verts=[]
    for z,r in profile:
        for j in range(seg):
            ang=2*math.pi*j/seg
            verts.append((loc[0]+r*math.cos(ang),loc[1]+r*math.sin(ang),z))
    faces=[]
    rings=len(profile)
    for ri in range(rings-1):
        for j in range(seg):
            n=(j+1)%seg
            a0=ri*seg+j; a1=ri*seg+n
            b0=(ri+1)*seg+j; b1=(ri+1)*seg+n
            faces.append((a0,a1,b1,b0))
    # close the ends
    verts.append((loc[0],loc[1],profile[0][0])); bot=len(verts)-1
    verts.append((loc[0],loc[1],profile[-1][0])); top=len(verts)-1
    for j in range(seg):
        n=(j+1)%seg
        faces.append((bot,n,j))
        a0=(rings-1)*seg+j; a1=(rings-1)*seg+n
        faces.append((top,a0,a1))
    mesh=bpy.data.meshes.new(name+"_mesh")
    mesh.from_pydata(verts,[],faces); mesh.update()
    # ED default material export requires a UV layer. Map U around the revolved circumference,
    # V along stack height so porcelain/grime textures remain stable and continuous.
    uv=mesh.uv_layers.new(name="UVMap")
    zmin=profile[0][0]; zmax=profile[-1][0]; zr=max(0.001,zmax-zmin)
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi=mesh.loops[li].vertex_index
            vx,vy,vz=mesh.vertices[vi].co
            dx=vx-loc[0]; dy=vy-loc[1]
            u=(math.atan2(dy,dx)/(2*math.pi))%1.0 if abs(dx)+abs(dy)>1e-8 else 0.5
            v=max(0.0,min(1.0,(vz-zmin)/zr))
            uv.data[li].uv=(u,v)
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    # continuous galvanized/copper core rod remains a separate simple object
    cyl(name+"_rod",loc,.033,height+.12,M["steel"],8 if detail<2 else 12)
    return o

def lattice_post(name,x,y,z0,h,M,detail=2,width=.72):
    # four-leg galvanized lattice with diagonal bracing
    for sx in (-1,1):
        for sy in (-1,1):
            box(f"{name}_leg_{sx}_{sy}",(x+sx*width/2,y+sy*width/2,z0+h/2),(.065,.065,h),M["galv"],.008)
    if detail>=1:
        steps=max(2,int(h/1.4))
        for j in range(steps+1):
            z=z0+h*j/steps
            box(f"{name}_ringx_{j}",(x,y,z),(width+.06,.045,.045),M["galv"],.006)
            box(f"{name}_ringy_{j}",(x,y,z),(.045,width+.06,.045),M["galv"],.006)
        if detail>=2:
            for j in range(steps):
                z=z0+h*(j+.5)/steps
                ang=math.radians(35)
                box(f"{name}_diagx_{j}",(x,y-width*.26,z),(width*.95,.035,.035),M["galv"],.004,rot=(0,ang,0))
                box(f"{name}_diagy_{j}",(x-width*.26,y,z),(.035,width*.95,.035),M["galv"],.004,rot=(ang,0,0))

def fan_guard(name,loc,r,M,detail=2,rot=(math.radians(90),0,0)):
    torus(name+"_rim",loc,r,.035,M["steel"],rot=rot,major_segments=24 if detail>=2 else 14,minor_segments=6)
    if detail>=2:
        for i in range(8):
            a=2*math.pi*i/8
            # spokes represented as thin bars in X/Z plane for face normal Y
            box(f"{name}_spoke_{i}",loc,(r*1.55,.025,.022),M["steel"],.003,rot=(0,-a,0))
        for i in range(5):
            rr=r*(i+1)/6
            torus(f"{name}_mesh_{i}",loc,rr,.008,M["steel"],rot=rot,major_segments=20,minor_segments=4)
    cyl(name+"_hub",loc,.09,.08,M["steel"],12,rot=rot)
