import os, math
from pathlib import Path
import bpy, numpy as np
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial

workspace = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
tex_dir = workspace / 'edm-jobs' / 'ground109_road_textures'
FT = 0.3048
KIND = os.environ.get('ROAD_KIND', 'straight').lower()
LENGTH_FT = float(os.environ.get('ROAD_LENGTH_FT', '30'))
TAG = os.environ.get('ROAD_TAG', '30FT')
ASSET = f'TPG_DIRT_SINGLE_LANE_{TAG}'

TRAVEL_W = 8.0 * FT
FEATHER = 0.5 * FT
OVERALL_W = 9.0 * FT
HALF_TOTAL = OVERALL_W / 2.0
HALF_TRAVEL = TRAVEL_W / 2.0
TERRAIN_Z = 0.010
ROAD_EDGE_Z = 0.085
CROWN_Z = 0.120
COLL_BOTTOM_Z = -1.0
TEX_SCALE_M = 2.0
RAMP = min(4.0, max(2.5, LENGTH_FT * 0.20)) * FT
OFFSETS = [-HALF_TOTAL, -HALF_TRAVEL, 0.0, HALF_TRAVEL, HALF_TOTAL]
PROFILE_Z = [TERRAIN_Z, ROAD_EDGE_Z, CROWN_Z, ROAD_EDGE_Z, TERRAIN_Z]

class MeshBuilder:
    def __init__(self):
        self.verts=[]; self.faces=[]; self.map={}
    def v(self, p):
        key=tuple(round(float(c), 6) for c in p)
        if key not in self.map:
            self.map[key]=len(self.verts); self.verts.append(tuple(float(c) for c in p))
        return self.map[key]
    def face(self, pts):
        self.faces.append(tuple(self.v(p) for p in pts))

def profile_z(offset, blend=1.0):
    a=abs(offset)
    if a <= HALF_TRAVEL:
        z = CROWN_Z - (CROWN_Z-ROAD_EDGE_Z)*(a/HALF_TRAVEL)
    else:
        z = ROAD_EDGE_Z + (TERRAIN_Z-ROAD_EDGE_Z)*((a-HALF_TRAVEL)/FEATHER)
    return TERRAIN_Z + blend*(z-TERRAIN_Z)

def add_ribbon(builder, centerline, blend_func):
    rows=[]
    n=len(centerline)
    for i,(x,y) in enumerate(centerline):
        if i==0: dx=centerline[1][0]-x; dy=centerline[1][1]-y
        elif i==n-1: dx=x-centerline[i-1][0]; dy=y-centerline[i-1][1]
        else: dx=centerline[i+1][0]-centerline[i-1][0]; dy=centerline[i+1][1]-centerline[i-1][1]
        mag=max(1e-9, math.hypot(dx,dy)); nx=-dy/mag; ny=dx/mag
        b=blend_func(i, centerline)
        row=[]
        for off in OFFSETS:
            row.append((x+nx*off, y+ny*off, profile_z(off,b)))
        rows.append(row)
    for j in range(n-1):
        for i in range(len(OFFSETS)-1):
            builder.face([rows[j][i], rows[j][i+1], rows[j+1][i+1], rows[j+1][i]])

def cumulative(points):
    d=[0.0]
    for i in range(1,len(points)):
        d.append(d[-1]+math.hypot(points[i][0]-points[i-1][0], points[i][1]-points[i-1][1]))
    return d

def end_ramp_blend(i, points):
    d=cumulative(points); total=d[-1]
    return max(0.0,min(1.0,d[i]/RAMP,(total-d[i])/RAMP))

def build_straight():
    L=LENGTH_FT*FT; h=L/2
    ys=[-h, -h+RAMP*0.5, -h+RAMP, h-RAMP, h-RAMP*0.5, h]
    pts=[(0.0,y) for y in ys]
    b=MeshBuilder(); add_ribbon(b,pts,end_ramp_blend); return b

def build_turn(left=False):
    # 90-degree single-lane elbow: 15 ft centerline radius + 12 ft tangent at each end.
    R=15.0*FT; T=12.0*FT
    pts=[(0.0,-T), (0.0,-T*0.5), (0.0,0.0)]
    # Right turn from northbound (+Y) to eastbound (+X); mirror X for left turn.
    cx=R
    for k in range(1,17):
        t=k/16.0; th=math.pi + (math.pi/2-math.pi)*t
        x=cx+R*math.cos(th); y=R*math.sin(th)
        pts.append(((-x if left else x), y))
    endx=(-R if left else R); endy=R
    pts += [(endx + (-T*0.5 if left else T*0.5), endy),
            (endx + (-T if left else T), endy)]
    b=MeshBuilder(); add_ribbon(b,pts,end_ramp_blend); return b

def add_grid(builder, xs, ys, zfun):
    grid=[]
    for y in ys:
        row=[]
        for x in xs: row.append((x,y,zfun(x,y)))
        grid.append(row)
    for j in range(len(ys)-1):
        for i in range(len(xs)-1):
            builder.face([grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]])

def build_junction(cross=False):
    b=MeshBuilder()
    coords=OFFSETS
    def pz(v): return profile_z(v,1.0)
    if cross:
        add_grid(b,coords,coords,lambda x,y:max(pz(x),pz(y)))
        dirs=[(0,-1),(0,1),(-1,0),(1,0)]
    else:
        # Horizontal road continues through; vertical stem enters from south and fades out at north cap.
        def zt(x,y):
            horiz=pz(y)
            fade=1.0 if y<=0 else max(0.0,1.0-y/HALF_TOTAL)
            vert=TERRAIN_Z + fade*(pz(x)-TERRAIN_Z)
            return max(horiz,vert)
        add_grid(b,coords,coords,zt)
        dirs=[(0,-1),(-1,0),(1,0)]
    ARM=12.0*FT
    for dx,dy in dirs:
        # Centerline begins at central-square edge at full road height and ramps to terrain at outer end.
        pts=[]
        for s in (HALF_TOTAL, HALF_TOTAL+ARM*0.45, HALF_TOTAL+ARM):
            pts.append((dx*s,dy*s))
        def one_end(i,p):
            if i==0:return 1.0
            if i==1:return 0.55
            return 0.0
        add_ribbon(b,pts,one_end)
    return b

if KIND=='straight': builder=build_straight()
elif KIND=='right': builder=build_turn(False)
elif KIND=='left': builder=build_turn(True)
elif KIND=='t': builder=build_junction(False)
elif KIND=='intersection': builder=build_junction(True)
else: raise RuntimeError(f'Unknown ROAD_KIND={KIND}')

mesh=bpy.data.meshes.new(ASSET+'_MESH')
mesh.from_pydata(builder.verts,[],builder.faces); mesh.update()
road=bpy.data.objects.new(ASSET,mesh); bpy.context.collection.objects.link(road)
uv=mesh.uv_layers.new(name='UVMap')
for poly in mesh.polygons:
    for li in poly.loop_indices:
        vi=mesh.loops[li].vertex_index; x,y,z=mesh.vertices[vi].co
        uv.data[li].uv=((x/TEX_SCALE_M)+0.5,(y/TEX_SCALE_M)+0.5)

# Native ED material using exact Ground109 maps.
mat=bpy.data.materials.new('TPG_Ground109_Dirt_PBR'); mat.use_nodes=True; mat.node_tree.nodes.clear()
desc=build_material_descriptions().get(DefaultMaterial.name)
if desc is None: raise RuntimeError('ED Default Material description missing')
edm=mat.node_tree.nodes.new(type=DefaultMaterial.node_group_name); edm.post_init(desc)

def tex(filename,socket,cs):
    path=tex_dir/filename
    img=bpy.data.images.load(str(path),check_existing=True)
    try: img.colorspace_settings.name=cs
    except Exception: pass
    node=mat.node_tree.nodes.new('ShaderNodeTexImage'); node.image=img; node.label=filename
    mat.node_tree.links.new(node.outputs['Color'],edm.inputs[socket])

ao=bpy.data.images.load(str(tex_dir/'Ground109_2K-PNG_AmbientOcclusion.png'),check_existing=True)
ro=bpy.data.images.load(str(tex_dir/'Ground109_2K-PNG_Roughness.png'),check_existing=True)
w,h=ao.size
a=np.array(ao.pixels[:],dtype=np.float32).reshape((-1,4))[:,0]
r=np.array(ro.pixels[:],dtype=np.float32).reshape((-1,4))[:,0]
out=np.empty((w*h,4),dtype=np.float32); out[:,0]=a; out[:,1]=r; out[:,2]=0; out[:,3]=1
rm=tex_dir/'TPG_Ground109_RoughMet.png'
ri=bpy.data.images.new('TPG_Ground109_RoughMet',width=w,height=h,alpha=True); ri.colorspace_settings.name='Non-Color'; ri.pixels.foreach_set(out.ravel()); ri.filepath_raw=str(rm); ri.file_format='PNG'; ri.save()
tex('Ground109_2K-PNG_Color.png','Base Color','sRGB')
tex('Ground109_2K-PNG_NormalGL.png','Normal (Non-Color)','Non-Color')
tex('TPG_Ground109_RoughMet.png','RoughMet (Non-Color)','Non-Color')
if edm.inputs.get('Base Alpha*'): edm.inputs['Base Alpha*'].default_value=1.0
road.data.materials.append(mat)

# Generic closed collision shell generated from the exact visible top footprint.
top=list(builder.verts); faces=list(builder.faces); n=len(top)
cverts=top+[(x,y,COLL_BOTTOM_Z) for x,y,z in top]
cfaces=list(faces)+[tuple(n+i for i in reversed(f)) for f in faces]
edge_count={}
for f in faces:
    for i in range(len(f)):
        a,b=f[i],f[(i+1)%len(f)]; key=tuple(sorted((a,b))); edge_count[key]=edge_count.get(key,0)+1
for (a,b),count in edge_count.items():
    if count==1: cfaces.append((a,b,n+b,n+a))
cm=bpy.data.meshes.new(ASSET+'_COLLISION_MESH'); cm.from_pydata(cverts,[],cfaces); cm.update()
col=bpy.data.objects.new(ASSET+'_COLLISION',cm); bpy.context.collection.objects.link(col)
if not hasattr(col,'EDMProps'): raise RuntimeError('EDM object properties missing')
col.EDMProps.SPECIAL_TYPE='COLLISION_SHELL'

road['TPG_SET']='TPG Dirt Single Lane Road Set'
road['ROAD_KIND']=KIND; road['LENGTH_FT']=LENGTH_FT if KIND=='straight' else 0
road['OVERALL_WIDTH_FT']=9.0; road['TRAVELED_WIDTH_FT']=8.0
road['NO_TEXTURED_VERTICAL_FACES']=True; road['COLLISION_BOTTOM_Z_M']=COLL_BOTTOM_Z
print(f'[TPG DIRT ROAD SET] built {ASSET}: kind={KIND}, verts={len(builder.verts)}, faces={len(builder.faces)}')
