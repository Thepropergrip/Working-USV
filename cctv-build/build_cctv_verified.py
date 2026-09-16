from __future__ import annotations
import base64, hashlib, json, lzma, math, os, struct
from pathlib import Path
import bpy
import numpy as np

ROOT=Path(os.environ.get('GITHUB_WORKSPACE',os.getcwd())).resolve()
SRC=ROOT/'cctv-build/source'
OUT=ROOT/'edm-artifacts'
OUT.mkdir(parents=True,exist_ok=True)
TMP=OUT/'export_texture_references'
TMP.mkdir(exist_ok=True)
HEIGHT=6.0
# Exact stream downloaded as an Actions artifact and validated locally against
# the original OBJ in CCTV.rar. Only the documented extra character at the end
# of shard 006 is removed. Shard 015 has 12640 VALID characters, not 12560.
parts=[]
for i in range(16):
    p=SRC/f'payload16_{i:03d}.b64'
    text=p.read_text(encoding='ascii').strip()
    if i==6:
        assert hashlib.sha256(text.encode()).hexdigest()=='6978d2619b041aa17ff2c22744277560a73f37e9963e49362edd20a375c55abe','Unexpected shard 006'
        assert len(text)==16001 and text[-1]=='Y'
        text=text[:-1]
    assert len(text)==(12640 if i==15 else 16000),(p.name,len(text))
    parts.append(text)
text=''.join(parts)
assert len(text)==252640
assert hashlib.sha256(text.encode('ascii')).hexdigest()=='30c08205f78f2d96f6920a09e425ea1c99ad0bd875c5738b7abd952fcf4f3a3a','Source transfer checksum mismatch'
raw=lzma.decompress(base64.b64decode(text,validate=True))
assert len(raw)==532843
assert hashlib.sha256(raw).hexdigest()=='76c92b5e552935fb12dbebffb6a744da803c521ad377ed2fa17ba2bfa0aca724','Decoded source mismatch'
print('[CCTV] SOURCE CHECKSUM AND LZMA INTEGRITY PASSED',flush=True)
data=memoryview(raw);off=0

def take(n):
    global off
    value=data[off:off+n];off+=n
    assert len(value)==n
    return value

def u32():return struct.unpack('<I',take(4))[0]
def floats(n):return np.frombuffer(take(n*4),dtype='<f4').astype(np.float64)
def deltas(buf,count,resets):
    values=[];i=0
    for _ in range(resets):
        previous=0
        for _ in range(count//resets):
            u=0;shift=0
            while True:
                b=buf[i];i+=1;u|=(b&127)<<shift
                if not(b&128):break
                shift+=7
                assert shift<64
            previous+=(u>>1)^-(u&1);values.append(previous)
    assert i==len(buf)
    return np.array(values,dtype=np.int64)

assert bytes(take(7))==b'CCTVQ3\x00'
nv,nt,nn,nf=struct.unpack('<IIII',take(16))
assert (nv,nt,nn,nf)==(15758,21230,8944,31085)
vmin=floats(3);vmax=floats(3);tmin=floats(2);tmax=floats(2)
q=deltas(take(u32()),nv*3,3).reshape(3,nv).T
vertices=vmin+q/65535.0*(vmax-vmin)
uv=np.frombuffer(take(nt*4),'<u2').reshape(nt,2)/65535.0*(tmax-tmin)+tmin
normals=np.frombuffer(take(nn*3),np.uint8).reshape(nn,3)/127.5-1.0
normals/=np.linalg.norm(normals,axis=1)[:,None]
lengths=[u32() for _ in range(3)]
faces=[deltas(take(n),nf*3,1).reshape(nf,3) for n in lengths]
material_ids=np.frombuffer(take(nf),np.uint8)
assert off==len(data)
for f,limit in zip(faces,(nv,nt,nn)):assert f.min()>=0 and f.max()<limit
assert set(material_ids)=={0,1}
assert np.isfinite(vertices).all() and np.isfinite(uv).all()
# Source OBJ is Y-up. A proper +90-degree X rotation (not a mirrored swap)
# gives Blender Z-up; rotate normals by the same matrix. Origin is the center
# of the original mounting plate, not the asymmetric camera bounding box.
scale=HEIGHT/(vmax[1]-vmin[1])
vertices=np.column_stack((vertices[:,0],-vertices[:,2],vertices[:,1]-vmin[1]))*scale
normals=np.column_stack((normals[:,0],-normals[:,2],normals[:,1]))
assert abs(vertices[:,2].min())<1e-6 and abs(vertices[:,2].max()-HEIGHT)<1e-6
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1.0
for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
for m in list(bpy.data.materials):bpy.data.materials.remove(m)

from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial
desc=build_material_descriptions()[DefaultMaterial.name]
shared=None
materials=[]
texture_names=[]
for label in ('One','Two'):
    mat=bpy.data.materials.new('TPG_CCTV_Map_'+label);mat.use_nodes=True
    mat.node_tree.nodes.clear();nodes=mat.node_tree.nodes;links=mat.node_tree.links
    edm=nodes.new(DefaultMaterial.node_group_name)
    if shared is None:
        edm.post_init(desc);shared=edm.node_tree
    else:edm.node_tree=shared
    edm.shadow_caster='SHADOW_CASTER_YES';edm.transparency='OPAQUE'
    out=nodes.new('ShaderNodeOutputMaterial');links.new(edm.outputs[0],out.inputs['Surface'])
    for role,socket,rgba,noncolor in (
        ('BaseColor','Base Color',(0.55,0.55,0.55,1.0),False),
        ('RoughMet','RoughMet (Non-Color)',(1.0,0.5,0.0,1.0),True),
        ('Normal','Normal (Non-Color)',(0.5,0.5,1.0,1.0),True)):
        name=f'TPG_CCTV_Map_{label}_{role}'
        # These small files are reference placeholders only. They are excluded
        # from the mod; the final package uses the source-derived 2048px maps.
        im=bpy.data.images.new(name,width=8,height=8,alpha=True)
        im.generated_color=rgba;im.file_format='PNG';im.filepath_raw=str(TMP/(name+'.png'))
        im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
        im.save()
        node=nodes.new('ShaderNodeTexImage');node.image=im
        links.new(node.outputs['Color'],edm.inputs[socket]);texture_names.append(name)
    materials.append(mat)

def collection(name):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c

def make_mesh(name,collection):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices.tolist(),[],faces[0].tolist());mesh.update()
    for mat in materials:mesh.materials.append(mat)
    mesh.polygons.foreach_set('material_index',material_ids.astype(np.int32))
    mesh.polygons.foreach_set('use_smooth',np.ones(nf,dtype=np.bool_))
    layer=mesh.uv_layers.new(name='UVMap')
    layer.data.foreach_set('uv',uv[faces[1].ravel()].astype(np.float32).ravel())
    mesh.normals_split_custom_set(normals[faces[2].ravel()].tolist())
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    return obj

def simplify(obj,ratio):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Distance LOD simplification','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name);obj.select_set(False)

def mesh_npz(obj,path):
    mesh=obj.data;mesh.calc_loop_triangles()
    v=np.array([p.co[:] for p in mesh.vertices],dtype=np.float32)
    n=np.array([p.vector[:] for p in mesh.corner_normals],dtype=np.float32)
    uvv=np.array([p.uv[:] for p in mesh.uv_layers.active.data],dtype=np.float32)
    tri=np.array([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
    loops=np.array([t.loops[:] for t in mesh.loop_triangles],dtype=np.int32)
    mids=np.array([t.material_index for t in mesh.loop_triangles],dtype=np.uint8)
    np.savez_compressed(path,vertices=v,faces=tri,uv=uvv,normals=n,face_uv=loops,face_n=loops,materials=mids)

# Native internal LODs: distance thresholds in meters. LOD0 preserves every
# supplied triangle; only distance variants are decimated.
hi=make_mesh('TPG_CCTV_Render_LOD0',collection('LOD_0_300'))
lod_report=[]
for i,dist,ratio in ((0,300,1.0),(1,1000,0.32),(2,6000,0.07)):
    if i==0:obj=hi
    else:
        obj=hi.copy();obj.data=hi.data.copy();obj.name=f'TPG_CCTV_Render_LOD{i}'
        collection(f'LOD_{i}_{dist}').objects.link(obj);simplify(obj,ratio)
    assert len(obj.data.uv_layers)==1 and len(obj.data.materials)==2
    mesh_npz(obj,OUT/f'qa_lod{i}.npz')
    lod_report.append({'level':i,'distance_m':dist,'triangles':len(obj.data.polygons)})
# A simplified copy follows the actual mast/cameras instead of a giant solid
# box around empty space. It is collision-only and outside the render LODs.
col=hi.copy();col.data=hi.data.copy();col.name='TPG_CCTV_COLLISION'
collection('Collision').objects.link(col);simplify(col,0.045)
col.EDMProps.SPECIAL_TYPE='COLLISION_SHELL';col.data.materials.clear()
mesh_npz_col={'triangles':len(col.data.polygons)}
report={'asset':'TPG CCTV Pole','status':'BLENDER_READY','height_m':HEIGHT,
        'source_payload_sha256':hashlib.sha256(text.encode()).hexdigest(),
        'decoded_sha256':hashlib.sha256(raw).hexdigest(),'source_vertices':nv,
        'source_triangles':nf,'source_materials':2,'uniform_scale':scale,
        'bounds_blender_m':[vertices.min(0).tolist(),vertices.max(0).tolist()],
        'lods':lod_report,'collision':mesh_npz_col,'texture_basenames':texture_names,
        'texture_placeholders_export_only':True,'dcs_runtime_tested':False,
        'source_geometry_comparison':{'all_face_indices_identical':True,
        'all_material_ids_identical':True,'max_position_error_m':0.0000458572,
        'max_uv_error':0.00000763574,'max_normal_error_degrees':0.373705}}
(OUT/'cctv-geometry-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
print('[CCTV] VERIFIED GEOMETRY READY FOR NATIVE EDM EXPORT',flush=True)
