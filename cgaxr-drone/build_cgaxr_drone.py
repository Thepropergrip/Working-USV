import base64,json,lzma,os,struct,gc
from pathlib import Path
import bpy
from materials.materials import build_material_descriptions
from materials.material_tools import createEdmNodeGroup
from enums import NodeSocketInDefaultEnum as D,NodeSocketInGlassEnum as G
from objects_custom_props import get_edm_props
W=Path(os.environ.get('GITHUB_WORKSPACE',os.getcwd())).resolve(); S=W/'cgaxr-drone'/'source'; A=W/'edm-artifacts'; T=A/'Textures';T.mkdir(parents=True,exist_ok=True)
MD=build_material_descriptions()
def parts(p):
 fs=sorted(S.glob(p+'.part*.b64'))
 if not fs: raise FileNotFoundError(p)
 return base64.b64decode(''.join(x.read_text(encoding='ascii').strip() for x in fs))
def vi(b):
 v=sh=0
 for x in b:
  v|=(x&127)<<sh
  if x&128: sh+=7
  else: yield v;v=sh=0
 if sh: raise ValueError('truncated varint')
def zz(z):return(z>>1)^-(z&1)
def qdec(b,n,mn,mx,bits):
 sc=(mx-mn)/((1<<bits)-1);o=[0.0]*n;pr=0;it=vi(b)
 for i in range(n):
  d=zz(next(it));q=d if i==0 else pr+d;pr=q;o[i]=mn+q*sc
 return o
def top(b,fs):
 it=vi(b);nn=0;o=[]
 for n in fs:
  f=[]
  for _ in range(n):
   c=next(it);x=nn if c==0 else nn-(c-1);nn+=c==0;f.append(x)
  o.append(f)
 return o
def uvidx(b,fs):
 it=vi(b);nn=0;o=[]
 for n in fs:
  f=[]
  for _ in range(n):
   c=next(it)
   if c==0:x=-1
   elif c==1:x=nn;nn+=1
   else:x=nn-(c-2)
   f.append(x)
  o.append(f)
 return o
def payload():
 r=lzma.decompress(parts('cgaxr_mesh_payload'));assert r[:7]==b'CGAXR3\0';p=7
 n=struct.unpack_from('<I',r,p)[0];p+=4;m=json.loads(r[p:p+n]);p+=n
 ns=struct.unpack_from('<I',r,p)[0];p+=4;s={}
 for _ in range(ns):
  n=struct.unpack_from('<H',r,p)[0];p+=2;k=r[p:p+n].decode();p+=n
  n=struct.unpack_from('<Q',r,p)[0];p+=8;s[k]=r[p:p+n];p+=n
 return m,s
def solid(n,c):
 p=T/(n+'.png');im=bpy.data.images.new(n,width=8,height=8,alpha=True);im.pixels=list(c)*64;im.filepath_raw=str(p);im.file_format='PNG';im.save();bpy.data.images.remove(im);return p
def texnode(m,p,non=False):
 n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(p),check_existing=True)
 if non:n.image.colorspace_settings.name='Non-Color'
 return n
def dmat(n,c,rough,metal,base=None):
 bp=base or solid(n+'_Base',(*c,1));rp=solid(n+'_RoughMet',(1,rough,metal,1));m=bpy.data.materials.new(n);m.use_nodes=True;m.node_tree.nodes.clear();g=createEdmNodeGroup('EDM_Default_Material',m);g.post_init(MD['EDM_Default_Material']);g.name='Group'
 m.node_tree.links.new(texnode(m,bp).outputs['Color'],g.inputs[D.BASE_COLOR]);m.node_tree.links.new(texnode(m,rp,True).outputs['Color'],g.inputs[D.ROUGH_METAL]);return m
def gmat(n,c,rough,metal,op):
 cp=solid(n+'_Filter',(*c,1));rp=solid(n+'_RoughMet',(1,rough,metal,1));m=bpy.data.materials.new(n);m.use_nodes=True;m.node_tree.nodes.clear();g=createEdmNodeGroup('EDM_Glass_Material',m);g.post_init(MD['EDM_Glass_Material']);g.name='Group'
 m.node_tree.links.new(texnode(m,cp).outputs['Color'],g.inputs[G.GLASS_COLOR]);m.node_tree.links.new(texnode(m,rp,True).outputs['Color'],g.inputs[G.ROUGH_METAL])
 if hasattr(g,'glass_transparency'):g.glass_transparency='ALPHA_BLENDING'
 if hasattr(g,'glass_shadow_caster'):g.glass_shadow_caster='SHADOW_CASTER_YES'
 if hasattr(g,'glass_type'):
  try:g.glass_type='GLASS_INSTRUMENTAL'
  except:pass
 try:g.inputs[G.OPACITY_VALUE].default_value=op
 except:pass
 return m
def main():
 m,s=payload();nv=m['vertex_count'];nu=m['uv_count'];pb=m['position_bounds'];ub=m['uv_bounds'];fs=s['face_sizes']
 x=qdec(s['px'],nv,*pb[0],m['position_bits']);y=qdec(s['py'],nv,*pb[1],m['position_bits']);z=qdec(s['pz'],nv,*pb[2],m['position_bits']);vs=list(zip(x,y,z));del x,y,z
 fsx=top(s['topology'],fs);u=qdec(s['uv_u'],nu,*ub[0],m['uv_bits']);v=qdec(s['uv_v'],nu,*ub[1],m['uv_bits']);uv=list(zip(u,v));del u,v;ufi=uvidx(s['uv_indices'],fs)
 lp=T/'CGAXR_Lense_01_DCS.jpg';lp.write_bytes(parts('CGAXR_Lense_01_DCS.jpg'))
 mats=[dmat('CGAXR_Plastic_Black',(0.008,)*3,.30,0),gmat('CGAXR_Frosted_Glass',(0.886,)*3,.15,0,.42),dmat('CGAXR_Aluminium',(0.702,.6892037,.661284),.51,.72),gmat('CGAXR_Clear_Glass',(.8470588,1,.9137255),.02,0,.20),dmat('CGAXR_Rim',(.2457,.2548,.273),.50,.72),dmat('CGAXR_Color_Shader',(.517,.41275,.16333),.36,.08)];lm=dmat('CGAXR_Camera_Lens_Texture',(1,1,1),.25,.02,lp);mats.append(lm);ls=len(mats)-1
 me=bpy.data.meshes.new('CGAXR_MC_Drone_Mesh');me.from_pydata(vs,[],fsx);me.update(calc_edges=True);o=bpy.data.objects.new('CGAXR_MC_Drone',me);bpy.context.collection.objects.link(o)
 for a in mats:me.materials.append(a)
 gr=m['groups'];mi=s['material_ids'];gi=s['group_ids']
 for i,p in enumerate(me.polygons):p.material_index=ls if 'CGAXR_MC_Drone_Camera14' in gr[gi[i]] else mi[i];p.use_smooth=True
 ul=me.uv_layers.new(name='UVMap');li=0
 for f in ufi:
  for j in f:ul.data[li].uv=uv[j] if j>=0 else(0,0);li+=1
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 try:
  wn=o.modifiers.new('Source_Shading_WeightedNormals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50
 except:pass
 bpy.ops.mesh.primitive_cube_add(size=1,location=(-.01,0,.27));c=bpy.context.object;c.name='CGAXR_MC_Drone_COLLISION';c.dimensions=(.55,.55,.48);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);get_edm_props(c).SPECIAL_TYPE='COLLISION_SHELL'
 print('[CGAXR] vertices',nv,'faces',m['face_count'],'loops',li,'uvs',nu,'bbox',pb)
 del vs,fsx,ufi,uv,mi,gi,s;gc.collect()
main()
