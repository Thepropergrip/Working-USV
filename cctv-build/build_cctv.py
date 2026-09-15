from __future__ import annotations
import base64, lzma, math, os, struct
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

TARGET_HEIGHT_M = 6.0
ROOT = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
SRC_DIR = ROOT / 'cctv-build' / 'source'
TMP_DIR = ROOT / 'cctv-build' / '_runtime'
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Rebuild a compact, loss-minimized copy of the creator's dedicated low-poly
# mesh. The payload retains every triangle, both UV/material assignments and the
# source vertex normals; positions/UVs use 16-bit quantization, which is far
# below a visible error at the final 6 m DCS scale.
b64 = ''.join(p.read_text(encoding='ascii').strip() for p in sorted(SRC_DIR.glob('part_*.b64')))
if not b64:
    raise RuntimeError('No CCTV source payload chunks found')
data = memoryview(lzma.decompress(base64.b64decode(b64)))
off = 0

def take(n):
    global off
    out = data[off:off+n]
    off += n
    return out

def u32():
    return struct.unpack('<I', take(4))[0]

def f32s(n):
    return struct.unpack('<' + ('f' * n), take(4*n))

def decode_delta(buf, count, resets=1):
    vals=[]; i=0
    each=count // resets
    for _ in range(resets):
        prev=0
        for _ in range(each):
            shift=0; u=0
            while True:
                b=buf[i]; i += 1
                u |= (b & 0x7f) << shift
                if not (b & 0x80): break
                shift += 7
            d=(u >> 1) ^ -(u & 1)
            prev += d
            vals.append(prev)
    if i != len(buf):
        raise RuntimeError(f'Delta stream length mismatch: consumed {i}, had {len(buf)}')
    return vals

if bytes(take(7)) != b'CCTVQ3\x00':
    raise RuntimeError('Unexpected CCTV payload format')
v_count, vt_count, vn_count, f_count = struct.unpack('<IIII', take(16))
vmin=f32s(3); vmax=f32s(3); uvmin=f32s(2); uvmax=f32s(2)
pos_len=u32(); pos_enc=take(pos_len)
pos_flat=decode_delta(pos_enc, v_count*3, resets=3)
# Position stream is stored one complete axis at a time.
pos_cols=[pos_flat[i*v_count:(i+1)*v_count] for i in range(3)]
uv_q=struct.unpack('<' + ('H'*(vt_count*2)), take(vt_count*2*2))
n_q=take(vn_count*3)
face_lens=(u32(),u32(),u32())
face_streams=[]
for ln in face_lens:
    face_streams.append(decode_delta(take(ln), f_count*3, resets=1))
face_mats=bytes(take(f_count))
if off != len(data):
    raise RuntimeError(f'Payload trailing bytes: {len(data)-off}')

obj_path=TMP_DIR/'cctv.obj'
mtl_path=TMP_DIR/'cctv.mtl'
mtl_path.write_text('''# TPG CCTV source material names\nnewmtl Map_One\nKd 0.8 0.8 0.8\nnewmtl Map_Two\nKd 0.8 0.8 0.8\n''', encoding='utf-8')
with obj_path.open('w', encoding='utf-8', newline='\n') as f:
    f.write('mtllib cctv.mtl\no TPG_CCTV_Source\n')
    for i in range(v_count):
        xyz=[vmin[a] + (pos_cols[a][i]/65535.0)*(vmax[a]-vmin[a]) for a in range(3)]
        f.write(f'v {xyz[0]:.7f} {xyz[1]:.7f} {xyz[2]:.7f}\n')
    for i in range(vt_count):
        uv=[]
        for a in range(2):
            q=uv_q[i*2+a]
            uv.append(uvmin[a] + (q/65535.0)*(uvmax[a]-uvmin[a]))
        f.write(f'vt {uv[0]:.7f} {uv[1]:.7f}\n')
    for i in range(vn_count):
        nn=[(n_q[i*3+a]/127.5)-1.0 for a in range(3)]
        mag=math.sqrt(sum(x*x for x in nn)) or 1.0
        nn=[x/mag for x in nn]
        f.write(f'vn {nn[0]:.7f} {nn[1]:.7f} {nn[2]:.7f}\n')
    f.write('s 1\n')
    last_mat=None
    for fi in range(f_count):
        mat='Map_One' if face_mats[fi] == 0 else 'Map_Two'
        if mat != last_mat:
            f.write(f'usemtl {mat}\n'); last_mat=mat
        corners=[]
        for c in range(3):
            k=fi*3+c
            corners.append(f'{face_streams[0][k]+1}/{face_streams[1][k]+1}/{face_streams[2][k]+1}')
        f.write('f ' + ' '.join(corners) + '\n')
print(f'[CCTV] Rebuilt source: {v_count} verts, {f_count} triangles, {vt_count} UVs, {vn_count} normals')

# Blender 4.1's native OBJ importer resolves the source Y-up convention into
# Blender Z-up. A dominant-axis fallback below protects against importer changes.
bpy.ops.wm.obj_import(filepath=str(obj_path))
mesh_objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
if not mesh_objs:
    raise RuntimeError('OBJ import produced no mesh objects')
print('[CCTV] Imported materials:', [m.name for m in bpy.data.materials])

# Bake transforms so DCS receives clean world-space geometry.
for obj in mesh_objs:
    if obj.data.users > 1: obj.data=obj.data.copy()
    mw=obj.matrix_world.copy()
    for v in obj.data.vertices: v.co=mw @ v.co
    obj.matrix_world=Matrix.Identity(4); obj.parent=None
for obj in list(bpy.context.scene.objects):
    if obj.type!='MESH': bpy.data.objects.remove(obj, do_unlink=True)

def bounds(objs):
    mn=Vector((1e30,1e30,1e30)); mx=Vector((-1e30,-1e30,-1e30))
    for o in objs:
        for v in o.data.vertices:
            c=v.co
            mn.x=min(mn.x,c.x); mn.y=min(mn.y,c.y); mn.z=min(mn.z,c.z)
            mx.x=max(mx.x,c.x); mx.y=max(mx.y,c.y); mx.z=max(mx.z,c.z)
    return mn,mx

mn,mx=bounds(mesh_objs); ext=mx-mn
print(f'[CCTV] Imported extents: {tuple(round(x,4) for x in ext)}')
if ext.z < max(ext.x,ext.y)*0.70:
    dominant=0 if ext.x>=ext.y else 1
    print(f'[CCTV] Remapping dominant {"X" if dominant==0 else "Y"} axis to Z')
    for o in mesh_objs:
        for v in o.data.vertices:
            x,y,z=v.co
            v.co=(z,y,x) if dominant==0 else (x,z,y)
    mn,mx=bounds(mesh_objs); ext=mx-mn
if ext.z<=0: raise RuntimeError('Invalid model height')
scale=TARGET_HEIGHT_M/ext.z
cx=(mn.x+mx.x)*0.5; cy=(mn.y+mx.y)*0.5
for o in mesh_objs:
    for v in o.data.vertices:
        v.co.x=(v.co.x-cx)*scale; v.co.y=(v.co.y-cy)*scale; v.co.z=(v.co.z-mn.z)*scale
mn2,mx2=bounds(mesh_objs)
print(f'[CCTV] Final bounds: min={tuple(round(x,3) for x in mn2)} max={tuple(round(x,3) for x in mx2)} height={mx2.z-mn2.z:.3f} m')

# ED native PBR materials. Tiny runtime images only cause the EDM to record the
# final texture names; the packaged mod supplies the real 2048x2048 maps.
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial
mat_desc=build_material_descriptions()[DefaultMaterial.name]
PNG_1X1=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL1WQAAAABJRU5ErkJggg==')
shared_tree=None

def temp_image(filename, non_color):
    p=TMP_DIR/filename; p.write_bytes(PNG_1X1)
    img=bpy.data.images.load(str(p), check_existing=False); img.name=filename; img.filepath=str(p)
    try: img.colorspace_settings.name='Non-Color' if non_color else 'sRGB'
    except Exception: pass
    return img

def texset_for(name, idx):
    n=name.lower().replace(' ','_')
    if 'map_one' in n or 'mapone' in n or 'map_1' in n: return 'Map_One'
    if 'map_two' in n or 'maptwo' in n or 'map_2' in n: return 'Map_Two'
    return 'Map_One' if idx==0 else 'Map_Two'

for idx,mat in enumerate(list(bpy.data.materials)):
    texset=texset_for(mat.name,idx)
    mat.use_nodes=True; nt=mat.node_tree; nt.nodes.clear()
    edm=nt.nodes.new(type=DefaultMaterial.node_group_name)
    if shared_tree is None:
        edm.post_init(mat_desc); shared_tree=edm.node_tree
    else: edm.node_tree=shared_tree
    try: edm.shadow_caster='SHADOW_CASTER_YES'; edm.transparency='OPAQUE'
    except Exception: pass
    for filename,socket,non_color in (
        (f'{texset}_BaseColor.png','Base Color',False),
        (f'{texset}_RoughMet.png','RoughMet (Non-Color)',True),
        (f'{texset}_Normal.png','Normal (Non-Color)',True)):
        node=nt.nodes.new('ShaderNodeTexImage'); node.image=temp_image(filename,non_color); node.name=filename
        nt.links.new(node.outputs['Color'],edm.inputs[socket])
    print(f'[CCTV] Material {mat.name!r} -> {texset}')

# Dedicated low-cost collision; it exports as collision only, never rendered.
def col_box(name,dims,center):
    bpy.ops.mesh.primitive_cube_add(size=1.0,location=center); o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.EDMProps.SPECIAL_TYPE='COLLISION_SHELL'
def col_cyl(name,radius,depth,z):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=radius,depth=depth,location=(0,0,z)); o=bpy.context.object; o.name=name
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.EDMProps.SPECIAL_TYPE='COLLISION_SHELL'
col_cyl('TPG_CCTV_COLLISION_POLE',0.18,5.35,2.675)
upper_w=max(0.8,min(2.4,(mx2.x-mn2.x)*0.95)); upper_d=max(0.8,min(2.4,(mx2.y-mn2.y)*0.95))
col_box('TPG_CCTV_COLLISION_HEAD',(upper_w,upper_d,0.75),(0,0,5.55))
for i,obj in enumerate(mesh_objs,1): obj.name=f'TPG_CCTV_VIS_{i:03d}'
print('[CCTV] Build prepared for native EDM export')
