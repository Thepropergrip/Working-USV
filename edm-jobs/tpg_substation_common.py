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

def _tex(name, base, variation=0.03, streak=False, soot=False, size=1024):
    path = TEXDIR / (name + ".png")
    if path.exists():
        return path
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    seed=zlib.crc32(name.encode("utf-8")) & 0xffffffff
    rng = random.Random(seed)
    phase1=rng.uniform(0,math.tau); phase2=rng.uniform(0,math.tau); phase3=rng.uniform(0,math.tau)
    stains=[]
    for _ in range(28 if soot else 7):
        stains.append((rng.random(),rng.random(),rng.uniform(.025,.18),rng.uniform(.025,.16),
                       rng.uniform(.08,.72) if soot else rng.uniform(.015,.07)))
    px=[]
    inv=max(1,size-1)
    is_gravel="Gravel" in name
    is_concrete="Concrete" in name or "BrickMortar" in name
    is_galv="Galvanized" in name
    is_porcelain="Porcelain" in name
    for y in range(size):
        v=y/inv
        for x in range(size):
            u=x/inv
            # Three spatial frequencies prevent the old uniform/random-pixel look.
            broad=(math.sin(u*math.tau*2.7+phase1)+math.sin(v*math.tau*2.1+phase2))*.25
            mid=math.sin((u*9.7+v*7.3)*math.tau+phase3)*.22
            fine=(rng.random()-.5)
            n=variation*(broad*.55+mid*.28+fine*.38)
            if streak:
                n += .010*math.sin(v*math.tau*18+phase2)+.006*math.sin((u*.7+v)*math.tau*31+phase1)
            if is_galv:
                n += .018*math.sin((u*21.0+v*13.0)*math.tau+phase1)*math.sin((u*7.0-v*11.0)*math.tau+phase2)
            if is_porcelain:
                n *= .28
                n += .004*math.sin(v*math.tau*34+phase3)
            if is_concrete:
                n += (rng.random()-.5)*.018
            if is_gravel:
                speck=rng.random()
                if speck>.965: n += rng.uniform(.035,.10)
                elif speck<.035: n -= rng.uniform(.025,.075)
            dark=0.0
            for cx,cy,rx,ry,p in stains:
                dx=(u-cx)/rx; dy=(v-cy)/ry
                d=dx*dx+dy*dy
                if d<1.0:
                    dark=max(dark,p*(1.0-d)**2)
            if not soot: dark*=.18
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
        rsz=256
        img=bpy.data.images.new(name+"_RoughMet",width=rsz,height=rsz,alpha=True)
        rr=random.Random((zlib.crc32((name+"_rmo").encode("utf-8")) & 0xffffffff))
        rp=[]
        for y in range(rsz):
            for x in range(rsz):
                u=x/(rsz-1); v=y/(rsz-1)
                wave=.5*math.sin((u*4.1+v*3.3)*math.tau)+.25*math.sin((u*13.0-v*9.0)*math.tau)
                rv=max(.04,min(.99,rough + wave*.028 + (rr.random()-.5)*.035))
                mv=max(0.0,min(1.0,metal + (rr.random()-.5)*(.025 if metal>.1 else .004)))
                rp.extend((1.0,rv,mv,1.0))
        img.pixels=rp
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
        mod=o.modifiers.new("edge_soften","BEVEL"); mod.width=bevel; mod.segments=4
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    if mat: o.data.materials.append(mat)
    if coll: get_edm_props(o).SPECIAL_TYPE="COLLISION_SHELL"
    return o

def cyl(name,loc,radius,depth,mat,verts=16,rot=(0,0,0),coll=False):
    if not coll:
        if radius >= .45: verts=max(verts,48)
        elif radius >= .12: verts=max(verts,36)
        else: verts=max(verts,24)
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name
    if not coll:
        # Smooth only barrel faces; preserve physically flat end caps.
        for p in o.data.polygons:
            p.use_smooth = abs(p.normal.z) < .90
        if radius >= .10 and depth >= .10:
            bev=o.modifiers.new("machined_edge","BEVEL")
            bev.width=min(.018,max(.004,radius*.035))
            bev.segments=3
            bpy.context.view_layer.objects.active=o
            bpy.ops.object.modifier_apply(modifier=bev.name)
    if mat: o.data.materials.append(mat)
    if coll: get_edm_props(o).SPECIAL_TYPE="COLLISION_SHELL"
    return o

def sphere(name,loc,r,mat,seg=16,rings=8):
    seg=max(seg,40); rings=max(rings,20)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,radius=r,location=loc)
    o=bpy.context.object; o.name=name
    for p in o.data.polygons: p.use_smooth=True
    if mat:o.data.materials.append(mat)
    return o

def torus(name,loc,major,minor,mat,rot=(0,0,0),major_segments=20,minor_segments=8):
    major_segments=max(major_segments,48); minor_segments=max(minor_segments,12)
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=major_segments,
        minor_segments=minor_segments,location=loc,rotation=rot)
    o=bpy.context.object;o.name=name
    for p in o.data.polygons: p.use_smooth=True
    if mat:o.data.materials.append(mat)
    return o

def text_obj(text,name,loc,size,mat,rot=(math.radians(90),0,0),extrude=.0,align="CENTER"):
    # Sign/label lettering is intentionally decal-flat: zero extrusion and zero bevel.
    # A tiny caller-controlled surface offset prevents z-fighting without making letters
    # appear as floating 3D signage.
    c=bpy.data.curves.new(name+"_curve","FONT"); c.body=text; c.align_x=align; c.align_y="CENTER"
    c.size=size; c.extrude=0.0; c.bevel_depth=0.0; c.bevel_resolution=0
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o)
    o.location=loc; o.rotation_euler=rot; o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.object.convert(target="MESH")
    bpy.context.object.name=name
    return bpy.context.object

def sign_plate(name,center,width,height,plate_mat,text,text_mat,M,text_size=.16,depth=.006,
               rot=(math.radians(90),0,0),subtext=None,subtext_mat=None,subtext_size=.10):
    # Industrial signage is a real thin plate with completely flat decal-style graphics.
    # Lettering has no extrusion/bevel and rides only 1.5 mm above the sign face.
    x,y,z=center
    box(name+"_PLATE",(x,y,z),(width,depth,height),plate_mat,0.0)
    face_y=y-depth/2-.0015
    text_z=z + (.10*height if subtext else 0.0)
    text_obj(text,name+"_TEXT",(x,face_y,text_z),text_size,text_mat,rot=rot)
    if subtext:
        text_obj(subtext,name+"_SUBTEXT",(x,face_y,z-.22*height),subtext_size,
                 subtext_mat or M["black"],rot=rot)
    return name

def danger_sign(name,center,M,width=1.60,height=.82):
    # Familiar utility warning placard: a thin white sign with a red DANGER header
    # and flat printed lettering. No lettering is physically extruded.
    x,y,z=center
    depth=.006
    box(name+"_PLATE",(x,y,z),(width,depth,height),M["white"],0.0)
    face_y=y-depth/2-.0015
    box(name+"_HEADER",(x,face_y+.0004,z+.20*height),(width*.94,.0015,height*.30),M["red"],0.0)
    text_obj("DANGER",name+"_HEADER_TEXT",(x,face_y-.001,z+.20*height),.17,M["white"])
    text_obj("HIGH VOLTAGE",name+"_HAZARD_TEXT",(x,face_y-.001,z-.17*height),.11,M["black"])
    return name

def equipment_label(name,center,M,text,width=1.10,height=.38,text_size=.13,plate="white",ink="black"):
    return sign_plate(name,center,width,height,M[plate],text,M[ink],M,text_size=text_size,depth=.005)

def _rounded_rect_ring(width,depth,radius,segments=8):
    # Counter-clockwise perimeter, starting near the lower-right corner.
    hw=width/2.0; hd=depth/2.0
    r=max(0.0,min(radius,hw-.001,hd-.001))
    pts=[]
    corners=[
        ( hw-r,-hd+r,-math.pi/2,0.0),
        ( hw-r, hd-r,0.0,math.pi/2),
        (-hw+r, hd-r,math.pi/2,math.pi),
        (-hw+r,-hd+r,math.pi,3*math.pi/2),
    ]
    for cx,cy,a0,a1 in corners:
        for j in range(segments):
            t=j/(segments-1) if segments>1 else 0.0
            a=a0+(a1-a0)*t
            p=(cx+r*math.cos(a),cy+r*math.sin(a))
            if not pts or (abs(p[0]-pts[-1][0])+abs(p[1]-pts[-1][1])>1e-6):
                pts.append(p)
    return pts

def foundation_bed(name,top_z=.3972,bottom_z=-.18,top_size=(120.0,90.0),bottom_size=(132.0,102.0),mat=None):
    # A true terrain-contact berm, not a floating slab.
    #
    # The top ring meets the underside of the raised yard.  A broad, continuous
    # sloped shoulder runs outward to a toe slightly below the DCS placement
    # plane, then a buried vertical skirt continues farther down.  The visible
    # slope therefore always intersects terrain instead of leaving daylight
    # beneath the yard. Rounded corners and quad strips avoid radial/triangle
    # lines across the berm.
    top_w,top_d=top_size
    bot_w,bot_d=bottom_size
    top_r=2.25
    toe_r=6.0
    seg=10
    top2=_rounded_rect_ring(top_w,top_d,top_r,seg)
    toe2=_rounded_rect_ring(bot_w,bot_d,toe_r,seg)
    if len(top2)!=len(toe2):
        raise RuntimeError("foundation ring topology mismatch")
    n=len(top2)
    toe_z=min(-0.08,bottom_z)
    skirt_z=min(-0.55,bottom_z-.30)

    verts=[]
    for x,y in top2: verts.append((x,y,top_z))
    for x,y in toe2: verts.append((x,y,toe_z))
    for x,y in toe2: verts.append((x,y,skirt_z))

    faces=[]
    # Sloped shoulder.
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,n+j,n+i))
    # Buried vertical skirt: prevents visible gaps on locally uneven DCS terrain.
    for i in range(n):
        j=(i+1)%n
        faces.append((n+i,n+j,2*n+j,2*n+i))
    # Bottom closure only; no top face, so there is no hidden coplanar surface
    # directly beneath the gravel cap.
    faces.append(tuple(range(3*n-1,2*n-1,-1)))

    mesh=bpy.data.meshes.new(name+"_mesh")
    mesh.from_pydata(verts,[],faces); mesh.update()

    # UV: U follows perimeter, V follows elevation, keeping the shoulder visually continuous.
    uv=mesh.uv_layers.new(name="UVMap")
    lengths=[0.0]
    total=0.0
    for i in range(n):
        j=(i+1)%n
        x0,y0=top2[i]; x1,y1=top2[j]
        total += math.hypot(x1-x0,y1-y0)
        lengths.append(total)
    total=max(total,1e-6)
    ring_u=[lengths[i]/total for i in range(n)]
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi=mesh.loops[li].vertex_index
            ring=vi//n
            idx=vi%n
            u=ring_u[idx]
            v=1.0 if ring==0 else (0.25 if ring==1 else 0.0)
            uv.data[li].uv=(u,v)
        # Smooth the berm shoulder/corners, while the buried skirt is irrelevant visually.
        if poly.index < n:
            poly.use_smooth=True

    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o)
    if mat: o.data.materials.append(mat)
    return o

def cable(name,pts,mat,radius=.022,res=1):
    c=bpy.data.curves.new(name+"_curve","CURVE"); c.dimensions="3D"; c.resolution_u=max(3,res+2); c.bevel_depth=radius; c.bevel_resolution=max(3,res+2); c.resolution_v=2
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
    # Reference-driven porcelain station/bushing insulator.
    # Broad umbrella sheds grow from a continuous ceramic trunk, with realistic
    # galvanized end caps/flanges. This intentionally avoids the old bead-like
    # sequence of rounded rings.
    mat=M["brown_porcelain"] if brown else M["porcelain"]

    if brown:
        core_r=.115
        shed_r=.305 if height>=2.6 else .275
        full_sheds=max(5,min(10,int(round(height/.40))))
    else:
        core_r=.090 if height>=2.8 else .105
        shed_r=.255 if height>=2.8 else .235
        full_sheds=max(6,min(13,int(round(height/.29))))

    if detail>=2:
        sheds=full_sheds
        seg=48
    elif detail==1:
        sheds=max(5,int(round(full_sheds*.72)))
        seg=32
    else:
        sheds=max(3,int(round(full_sheds*.46)))
        seg=16

    cap_h=min(.16,max(.10,height*.045))
    z_bottom=loc[2]-height/2
    z_top=loc[2]+height/2
    ceramic_bottom=z_bottom+cap_h
    ceramic_top=z_top-cap_h
    ceramic_h=max(.25,ceramic_top-ceramic_bottom)
    step=ceramic_h/sheds

    profile=[]
    # Bottom ceramic collar.
    profile.extend([
        (ceramic_bottom,core_r*1.24),
        (ceramic_bottom+step*.10,core_r*1.18),
        (ceramic_bottom+step*.15,core_r),
    ])

    for i in range(sheds):
        base=ceramic_bottom+i*step
        # Real porcelain weather shed: narrow trunk, sloping upper bell,
        # broad thin umbrella lip, then a sharper underside return.
        alt=1.0 if (brown or i%2==0) else .92
        sr=shed_r*alt
        profile.extend([
            (base+step*.16,core_r),
            (base+step*.23,core_r*1.10),
            (base+step*.29,sr*.48),
            (base+step*.35,sr*.72),
            (base+step*.40,sr*.92),
            (base+step*.44,sr),
            (base+step*.48,sr*.995),
            (base+step*.52,sr*.88),
            (base+step*.57,sr*.62),
            (base+step*.62,core_r*1.22),
            (base+step*.72,core_r),
            (base+step*.92,core_r),
        ])

    # Top ceramic collar.
    profile.extend([
        (ceramic_top-step*.08,core_r),
        (ceramic_top-step*.03,core_r*1.16),
        (ceramic_top,core_r*1.24),
    ])

    # Remove any accidental non-monotonic Z duplicates introduced where sections meet.
    clean=[]
    last_z=-1e30
    for z,r in profile:
        z=max(z,last_z+1e-5)
        clean.append((z,r))
        last_z=z
    profile=clean

    verts=[]
    for z,r in profile:
        for j in range(seg):
            a=2*math.pi*j/seg
            verts.append((loc[0]+r*math.cos(a),loc[1]+r*math.sin(a),z))
    faces=[]
    rings=len(profile)
    for ri in range(rings-1):
        for j in range(seg):
            nj=(j+1)%seg
            faces.append((ri*seg+j,ri*seg+nj,(ri+1)*seg+nj,(ri+1)*seg+j))

    # Ceramic end caps close the lathed porcelain body.
    verts.append((loc[0],loc[1],profile[0][0])); bot=len(verts)-1
    verts.append((loc[0],loc[1],profile[-1][0])); top=len(verts)-1
    for j in range(seg):
        nj=(j+1)%seg
        faces.append((bot,j,nj))
        a0=(rings-1)*seg+j; a1=(rings-1)*seg+nj
        faces.append((top,a1,a0))

    mesh=bpy.data.meshes.new(name+"_mesh")
    mesh.from_pydata(verts,[],faces); mesh.update()

    uv=mesh.uv_layers.new(name="UVMap")
    zmin=profile[0][0]; zmax=profile[-1][0]; zr=max(.001,zmax-zmin)
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi=mesh.loops[li].vertex_index
            vx,vy,vz=mesh.vertices[vi].co
            dx=vx-loc[0]; dy=vy-loc[1]
            u=(math.atan2(dy,dx)/(2*math.pi))%1.0 if abs(dx)+abs(dy)>1e-8 else .5
            v=max(0.0,min(1.0,(vz-zmin)/zr))
            uv.data[li].uv=(u,v)
        poly.use_smooth=True

    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)

    # Cast/galvanized mounting hardware like real station-post and transformer bushings.
    flange_r=max(core_r*1.75,shed_r*.56)
    neck_r=core_r*1.28
    verts_hw=36 if detail>=2 else (24 if detail==1 else 16)
    cyl(name+"_BASE_FLANGE",(loc[0],loc[1],z_bottom+cap_h*.28),flange_r,cap_h*.34,M["galv"],verts_hw)
    cyl(name+"_BASE_NECK",(loc[0],loc[1],z_bottom+cap_h*.66),neck_r,cap_h*.78,M["galv"],verts_hw)
    cyl(name+"_TOP_NECK",(loc[0],loc[1],z_top-cap_h*.66),neck_r,cap_h*.78,M["galv"],verts_hw)
    cyl(name+"_TOP_CAP",(loc[0],loc[1],z_top-cap_h*.23),max(core_r*1.55,shed_r*.48),cap_h*.38,M["galv"],verts_hw)

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