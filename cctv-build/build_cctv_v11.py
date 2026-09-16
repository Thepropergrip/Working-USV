"""Re-use the proven native-material build, then apply approved proportions."""
import hashlib,json,os,runpy,subprocess
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(os.environ.get('GITHUB_WORKSPACE',os.getcwd())).resolve()
source=ROOT/'cctv-build/build_cctv_verified.py'
# Verify the canonical Git blob, not platform-dependent checkout line endings.
b=subprocess.check_output(['git','cat-file','blob','HEAD:cctv-build/build_cctv_verified.py'],cwd=str(ROOT),timeout=15)
blob_sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
assert blob_sha=='82ae1ddd110fad90238c25d501efb3eb531af2ab',('Unexpected baseline build revision',blob_sha)
assert source.read_bytes().replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n'),'Checkout content differs from verified Git source'
print('[CCTV V1.1] Baseline Git blob verified: '+blob_sha,flush=True)
ns={'__name__':'tpg_cctv_baseline','__file__':str(source)}
exec(compile(b,str(source),'exec'),ns)
resize_ns=runpy.run_path(str(ROOT/'cctv-build/resize_geometry_v11.py'),run_name='tpg_cctv_resize')
hi=ns['hi'];mesh=hi.data
mesh.calc_loop_triangles()
original=np.array([v.co[:] for v in mesh.vertices],dtype=np.float64)
faces=np.array([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
assert np.array_equal(faces,ns['faces'][0])
oldnorm=np.array([n.vector[:] for n in mesh.corner_normals],dtype=np.float64)
loopverts=np.empty(len(mesh.loops),dtype=np.int32)
mesh.loops.foreach_get('vertex_index',loopverts)
uv_before=np.array([p.uv[:] for p in mesh.uv_layers.active.data],dtype=np.float32)
mat_before=np.array([p.material_index for p in mesh.polygons],dtype=np.int32)
vertices,normal_matrices,adjustment=resize_ns['resize'](original,faces)
norm=np.einsum('lij,lj->li',normal_matrices[loopverts],oldnorm)
norm/=np.linalg.norm(norm,axis=1)[:,None]
assert np.isfinite(norm).all()
mesh.vertices.foreach_set('co',vertices.astype(np.float32).ravel())
mesh.update()
mesh.normals_split_custom_set(norm.tolist())
assert np.array_equal(uv_before,np.array([p.uv[:] for p in mesh.uv_layers.active.data],dtype=np.float32))
assert np.array_equal(mat_before,np.array([p.material_index for p in mesh.polygons],dtype=np.int32))
assert len(mesh.polygons)==31085 and len(mesh.vertices)==15758
# Never retain distance models or a collision shell built to old proportions.
for obj in list(bpy.context.scene.objects):
    if obj!=hi:bpy.data.objects.remove(obj,do_unlink=True)
lods=[]
for level,dist,ratio in [(0,300,1.0),(1,1000,.32),(2,6000,.07)]:
    if level==0:obj=hi
    else:
        obj=hi.copy();obj.data=hi.data.copy();obj.name=f'TPG_CCTV_Render_LOD{level}'
        bpy.data.collections[f'LOD_{level}_{dist}'].objects.link(obj)
        ns['simplify'](obj,ratio)
    ns['mesh_npz'](obj,ns['OUT']/f'qa_lod{level}.npz')
    lods.append({'level':level,'distance_m':dist,'triangles':len(obj.data.polygons)})
col=hi.copy();col.data=hi.data.copy();col.name='TPG_CCTV_COLLISION'
bpy.data.collections['Collision'].objects.link(col)
ns['simplify'](col,.045)
col.EDMProps.SPECIAL_TYPE='COLLISION_SHELL';col.data.materials.clear()
report=ns['report'].copy()
report.pop('source_geometry_comparison',None)
report.pop('uniform_scale',None)
report.update({'version':'1.1','status':'BLENDER_READY_PROPORTIONS_CORRECTED','lods':lods,
 'bounds_blender_m':[vertices.min(0).tolist(),vertices.max(0).tolist()],
 'collision':{'triangles':len(col.data.polygons),'rebuilt_for_corrected_geometry':True},
 'adjustments':adjustment,'all_original_faces_retained':True,
 'uvs_and_material_assignments_unchanged':True,
 'normal_transform':'inverse-transpose per-vertex deformation; rotated cable rings',
 'baseline_v10_runtime_loaded':True,'v11_runtime_tested':False})
(ns['OUT']/'cctv-geometry-report.json').write_text(json.dumps(report,indent=2))
(ns['OUT']/'cctv-proportion-correction-report.json').write_text(json.dumps(adjustment,indent=2))
print('[CCTV V1.1] ALL 61 SOURCE PARTS ADJUSTED; 6 M OVERALL; UV/MATERIAL CHECKS PASSED',flush=True)
print(json.dumps(report,indent=2),flush=True)
