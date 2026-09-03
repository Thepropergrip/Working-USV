import bpy, math, os, io, base64, json, glob
from pathlib import Path
import numpy as np
WORK=Path(os.environ.get('GITHUB_WORKSPACE',os.getcwd())).resolve(); TEXDIR=WORK/'edm-artifacts'/'Textures'; TEXDIR.mkdir(parents=True,exist_ok=True)
from materials.materials import build_material_descriptions
from materials.material_tools import createEdmNodeGroup
from enums import NodeSocketInDefaultEnum
from objects_custom_props import get_edm_props
MAT_DESCS=build_material_descriptions(); M={}; LOD=int(os.environ.get('TPG_TACOMA_LOD','0')); DESTROYED=os.environ.get('TPG_TACOMA_DESTROYED','0')=='1'

def payload():
    parts=sorted((WORK/'edm-jobs'/'tacoma_fbx_mesh_b64').glob('part*.txt'))
    raw=base64.b64decode(''.join(p.read_text().strip() for p in parts)); z=np.load(io.BytesIO(raw),allow_pickle=False)
    meta=json.loads(str(z['meta'])); return z,meta

def tex(name,c,rough=.7,metal=0):
    p=TEXDIR/(name+'.png'); rp=TEXDIR/(name+'_RoughMet.png')
    if not p.exists():
        im=bpy.data.images.new(name,width=8,height=8,alpha=True); im.pixels=list(c+(1.0,))*64; im.filepath_raw=str(p); im.file_format='PNG'; im.save()
    if not rp.exists():
        im=bpy.data.images.new(name+'_RoughMet',width=8,height=8,alpha=True); im.pixels=[1,rough,metal,1]*64; im.filepath_raw=str(rp); im.file_format='PNG'; im.save()
    return p,rp

def mat(name,c,rough=.7,metal=0):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.node_tree.nodes.clear(); g=createEdmNodeGroup('EDM_Default_Material',m); g.post_init(MAT_DESCS['EDM_Default_Material']); g.name='Group'; p,rp=tex(name,c,rough,metal)
    n=m.node_tree.nodes.new('ShaderNodeTexImage'); n.image=bpy.data.images.load(str(p),check_existing=True); m.node_tree.links.new(n.outputs['Color'],g.inputs[NodeSocketInDefaultEnum.BASE_COLOR])
    n2=m.node_tree.nodes.new('ShaderNodeTexImage'); n2.image=bpy.data.images.load(str(rp),check_existing=True); n2.image.colorspace_settings.name='Non-Color'; m.node_tree.links.new(n2.outputs['Color'],g.inputs[NodeSocketInDefaultEnum.ROUGH_METAL]); return m

def materials():
    if M:return
    M.update(paint=mat('TPG_TACOMA_Quicksand_4T8',(.585,.525,.414),.42,.04), black=mat('TPG_TACOMA_Black',(.025,.027,.028),.76,.10), metal=mat('TPG_TACOMA_BlackMetal',(.018,.020,.021),.45,.72), rubber=mat('TPG_TACOMA_Rubber',(.015,.016,.016),.94,.01), glass=mat('TPG_TACOMA_TintedGlass',(.018,.035,.043),.16,.06), lamp=mat('TPG_TACOMA_Lamp',(.72,.78,.80),.13,.05), red=mat('TPG_TACOMA_RedLens',(.58,.018,.015),.22,.03), amber=mat('TPG_TACOMA_AmberLens',(.88,.28,.012),.20,.03), rim=mat('TPG_TACOMA_Wheel',(.11,.12,.13),.30,.78), brake=mat('TPG_TACOMA_BrakeRed',(.55,.012,.006),.35,.25), white=mat('TPG_TACOMA_White',(.80,.82,.80),.35,.02), blue=mat('TPG_TACOMA_PlateBlue',(.02,.08,.28),.42,.02), burnt=mat('TPG_TACOMA_Burnt',(.050,.037,.028),.90,.18), soot=mat('TPG_TACOMA_Soot',(.010,.009,.008),.98,.01))

def mesh(name,verts,faces,mats,mi=None,coll=False):
    me=bpy.data.meshes.new(name+'_mesh'); me.from_pydata(verts,[],faces); me.update(); o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    for x in mats: me.materials.append(x)
    if mi is not None:
        for i,p in enumerate(me.polygons): p.material_index=int(mi[min(i,len(mi)-1)]) if len(mi) else 0
    uv=me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        co=me.vertices[loop.vertex_index].co; uv.data[loop.index].uv=((co.x*.18+co.y*.13)%1,(co.z*.32+co.y*.17)%1)
    for p in me.polygons:p.use_smooth=True
    if coll:get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    return o

def faces(idx):
    out=[]; cur=[]
    for v in idx:
        v=int(v)
        if v<0: cur.append(-v-1); out.append(cur); cur=[]
        else:cur.append(v)
    return [f for f in out if len(f)>=3]

def box(name,loc,size,ma,bevel=.02,rot=(0,0,0),coll=False,parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot); o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=o.modifiers.new('soft','BEVEL');m.width=bevel;m.segments=3 if LOD<2 else 1;bpy.context.view_layer.objects.active=o
        try:bpy.ops.object.modifier_apply(modifier=m.name)
        except:pass
    if ma:o.data.materials.append(ma)
    if coll:get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    if parent:parent_keep(o,parent)
    return o

def cyl(name,loc,r,d,ma,verts=24,rot=(0,0,0),parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=d,location=loc,rotation=rot);o=bpy.context.object;o.name=name;o.data.materials.append(ma)
    if parent:parent_keep(o,parent)
    return o

def torus(name,loc,maj,minr,ma,rot=(0,0,0),parent=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=maj,minor_radius=minr,major_segments=32,minor_segments=8,location=loc,rotation=rot);o=bpy.context.object;o.name=name;o.data.materials.append(ma)
    if parent:parent_keep(o,parent)
    return o

def parent_keep(ch,pa):mw=ch.matrix_world.copy();ch.parent=pa;ch.matrix_world=mw

def tube(name,pts,r,ma):
    c=bpy.data.curves.new(name+'C','CURVE');c.dimensions='3D';c.bevel_depth=r;c.bevel_resolution=2;s=c.splines.new('POLY');s.points.add(len(pts)-1)
    for p,co in zip(s.points,pts):p.co=(*co,1)
    o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);c.materials.append(ma);return o

def text_obj(txt,name,loc,size,ma,rot=(math.pi/2,0,0)):
    c=bpy.data.curves.new(name+'C','FONT');c.body=txt;c.align_x='CENTER';c.align_y='CENTER';c.size=size;o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=rot;c.materials.append(ma);return o

def anim_rot(obj,arg,axis,neg,pos):
    act=bpy.data.actions.new(f'{arg}_{obj.name}');obj.animation_data_create();obj.animation_data.action=act
    for fr,a in ((0,neg),(100,0),(200,pos)):
        obj.rotation_euler=[0,0,0];obj.rotation_euler[axis]=a;obj.keyframe_insert('rotation_euler',frame=fr)
    for fc in act.fcurves:
        for k in fc.keyframe_points:k.interpolation='LINEAR'

def add_base():
    z,meta=payload(); mapping={'body':M['paint'],'black':M['black'],'plastic':M['black'],'glass':M['glass'],'front light':M['lamp'],'back light ':M['red'],'Material.007':M['rim'],'Material.008':M['brake'],'Material.009':M['rubber']}
    wheel_objs=[]
    for info in meta['geometries']:
        n=info['name']; v=z[n+'_v'].astype(float); f=faces(z[n+'_p']); srcm=info['materials']; mats=[mapping.get(x,M['black']) for x in srcm]; mi=z[n+'_mat']
        if DESTROYED and n=='Plane.001':mats=[M['burnt'] if x==mapping.get('body') else x for x in mats]
        o=mesh('FBX_'+n,v,f,mats,mi)
        if LOD:
            dec=o.modifiers.new('LOD','DECIMATE');dec.ratio=.55 if LOD==1 else .28;bpy.context.view_layer.objects.active=o
            try:bpy.ops.object.modifier_apply(modifier=dec.name)
            except:pass
        if n.startswith('Cylinder') and n!='Cylinder.004':wheel_objs.append(o)
    for o in wheel_objs:
        xs=[v.co.x for v in o.data.vertices];ys=[v.co.y for v in o.data.vertices];zs=[v.co.z for v in o.data.vertices]; c=((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2)
        steer=bpy.data.objects.new(o.name+'_STEER',None);steer.location=c;bpy.context.collection.objects.link(steer); roll=bpy.data.objects.new(o.name+'_ROLL',None);roll.location=c;bpy.context.collection.objects.link(roll);parent_keep(roll,steer);parent_keep(o,roll)
        anim_rot(roll,8,1,-2*math.pi,2*math.pi)
        if c[0]>0:anim_rot(steer,9,2,math.radians(-30),math.radians(30))

def add_custom():
    p=M['burnt'] if DESTROYED else M['paint']
    box('CAMPER_BODY',(-1.82,0,1.38),(1.65,1.72,.62),p,.08); box('CAMPER_ROOF',(-1.82,0,1.72),(1.70,1.78,.12),p,.05)
    for s in (-1,1):box(f'CAMPER_SIDE_GLASS_{s}',(-1.82,s*.872,1.47),(1.18,.018,.40),M['glass'],.025)
    box('CAMPER_REAR_GLASS',(-2.66,0,1.46),(.018,1.42,.42),M['glass'],.025)
    for cx,l,z in ((.25,1.45,1.87),(-1.84,1.48,1.88)):
        for s in (-1,1):box(f'RACK_RAIL_{cx}_{s}',(cx,s*.76,z),(l,.05,.08),M['metal'],.012)
        for i in range(6 if LOD==0 else 3):
            x=cx-l*.43+i*l*.86/((6 if LOD==0 else 3)-1);box(f'RACK_BAR_{cx}_{i}',(x,0,z),(.04,1.48,.035),M['metal'],.006)
    for s in (-1,1):
        x=1.09;y=s*.89;z=1.49;tube(f'DITCH_BRACKET_{s}',[(1.02,s*.79,1.33),(1.08,y,1.42)],.017,M['metal']);box(f'BLACK_OAK_{s}',(x,y,z),(.16,.18,.16),M['metal'],.022)
        for dy in (-.035,.035):
            for dz in (-.035,.035):cyl(f'BLACK_OAK_LED_{s}_{dy}_{dz}',(x+.086,y+dy,z+dz),.019,.010,M['lamp'],12,rot=(0,math.pi/2,0))
        if LOD==0:
            for i in range(5):box(f'BLACK_OAK_FIN_{s}_{i}',(x-.085-i*.014,y,z),(.009,.185,.15),M['black'],.001)
    for s in (-1,1):
        tube(f'SLIDER_MAIN_{s}',[(-1.05,s*1.0,.53),(1.02,s*1.0,.53)],.040,M['metal']);tube(f'SLIDER_INNER_{s}',[(-1.00,s*.89,.53),(.98,s*.89,.53)],.030,M['metal'])
        for x in (-.75,-.20,.40,.88):tube(f'SLIDER_BRACE_{s}_{x}',[(x,s*.78,.49),(x,s*.98,.53)],.023,M['metal'])
    box('REAR_BUMPER',(-2.86,0,.62),(.24,1.88,.24),M['metal'],.035)
    for s in (-1,1):
        box(f'REAR_WING_{s}',(-2.84,s*.76,.68),(.30,.34,.28),M['metal'],.025);box(f'REAR_AMBER_{s}',(-2.995,s*.56,.69),(.018,.20,.09),M['amber'],.010);torus(f'RECOVERY_{s}',(-2.99,s*.32,.50),.062,.015,M['metal'],rot=(0,math.pi/2,0))
    box('REAR_PLATE',(-2.995,0,.72),(.015,.31,.155),M['white'],.008);text_obj('DCS 4X4','REAR_PLATE_TEXT',(-3.005,0,.72),.052,M['blue'],rot=(math.pi/2,0,-math.pi/2))
    if LOD==0:
        for s in (-1,1):
            rot=(-math.pi/2,0,0) if s>0 else (math.pi/2,0,0);text_obj('TACOMA',f'TACOMA_BADGE_{s}',(.52,s*.958,1.02),.075,M['black'],rot);text_obj('TRD',f'TRD_{s}',(-2.02,s*.958,1.28),.076,M['black'],rot);text_obj('4X4',f'4X4_{s}',(-1.88,s*.959,1.28),.054,M['red'],rot);text_obj('OFF ROAD',f'OFFROAD_{s}',(-1.95,s*.958,1.22),.032,M['black'],rot)

def destroyed():
    if not DESTROYED:return
    box('WRECK_HOOD',(1.90,.05,1.18),(1.15,1.40,.08),M['soot'],.035,rot=(0,math.radians(8),math.radians(3)));box('WRECK_CAP_PANEL',(-1.95,.55,1.45),(1.05,.05,.55),M['soot'],.02,rot=(math.radians(10),0,math.radians(-12)));tube('BENT_RACK',[(-2.40,.70,1.72),(-1.78,.60,1.52),(-1.14,.54,1.46)],.045,M['burnt'])

def collision():
    box('COLLISION_MAIN',(0,0,1.0),(4.65,1.72,1.30),None,0,coll=True);box('COLLISION_NOSE',(2.30,0,.88),(1.15,1.75,.85),None,0,coll=True);box('COLLISION_REAR',(-2.30,0,1.05),(1.25,1.78,1.45),None,0,coll=True)

def build():
    materials();bpy.context.scene.frame_start=0;bpy.context.scene.frame_end=200;add_base();add_custom();destroyed();collision();bpy.context.scene.frame_set(100)
    for o in bpy.context.scene.objects:
        if o.type=='MESH' and o.material_slots:
            for p in o.data.polygons:
                if p.material_index>=len(o.material_slots):p.material_index=0
    print(f'[TPG TACOMA FBX V3] LOD={LOD} destroyed={DESTROYED} objects={len(bpy.context.scene.objects)} frame=100 neutral')
build()
