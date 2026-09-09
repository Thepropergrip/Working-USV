from __future__ import annotations

import base64
import lzma
import math
import os
import struct
from pathlib import Path

import bpy
import numpy as np
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial

ROOT = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
PARTDIR = ROOT / 'container-build-payload-q'
ART = ROOT / 'edm-artifacts'
ART.mkdir(parents=True, exist_ok=True)

# Reassemble the verified compact mesh payload in lexical order.
parts = sorted(PARTDIR.glob('part*.txt'))
if not parts:
    raise FileNotFoundError(f'No compact mesh payload chunks in {PARTDIR}')
encoded = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
if len(encoded) != 76464:
    raise RuntimeError(f'Compact payload length mismatch: {len(encoded)} != 76464')
raw = lzma.decompress(base64.b64decode(encoded, validate=True))

# TPGQ1 layout:
# magic[5], uint32 vertex_count, uint32 face_count,
# float32 origin xyz, float32 quantization_step xyz,
# uint16 xyz vertices, uint16 triangle indices.
if raw[:5] != b'TPGQ1':
    raise RuntimeError(f'Bad compact mesh magic: {raw[:5]!r}')
vertex_count, face_count = struct.unpack_from('<II', raw, 5)
origin_step = struct.unpack_from('<6f', raw, 13)
origin = np.asarray(origin_step[:3], dtype=np.float64)
step = np.asarray(origin_step[3:], dtype=np.float64)
expected = 37 + vertex_count * 3 * 2 + face_count * 3 * 2
if len(raw) != expected:
    raise RuntimeError(f'Compact mesh byte count mismatch: {len(raw)} != {expected}')
if vertex_count != 7613 or face_count != 14999:
    raise RuntimeError(f'Unexpected optimized mesh counts: vertices={vertex_count} faces={face_count}')

offset = 37
qv = np.frombuffer(raw, dtype='<u2', count=vertex_count * 3, offset=offset).reshape(vertex_count, 3)
offset += vertex_count * 3 * 2
faces = np.frombuffer(raw, dtype='<u2', count=face_count * 3, offset=offset).reshape(face_count, 3)
if int(faces.max()) >= vertex_count:
    raise RuntimeError('Compact mesh contains an out-of-range vertex index')
verts = origin + qv.astype(np.float64) * step

# Center the full visual footprint in X/Y and ground the model at Z=0.
mins = verts.min(axis=0)
maxs = verts.max(axis=0)
verts[:, 0] -= (mins[0] + maxs[0]) * 0.5
verts[:, 1] -= (mins[1] + maxs[1]) * 0.5
verts[:, 2] -= mins[2]

mesh = bpy.data.meshes.new('TPG_10FT_CONTAINER_OPEN_LITE_MESH')
mesh.from_pydata(verts.tolist(), [], faces.tolist())
mesh.update(calc_edges=True)
render = bpy.data.objects.new('TPG_10FT_CONTAINER_OPEN_LITE_RENDER', mesh)
bpy.context.collection.objects.link(render)
for poly in mesh.polygons:
    poly.use_smooth = False

# Compact UV layout. The modeled corrugation supplies macro surface relief;
# textures supply paint/steel response without carrying CAD-size texture sets.
bpy.context.view_layer.objects.active = render
render.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.018)
bpy.ops.object.mode_set(mode='OBJECT')

# 512px PBR maps: visually useful but intentionally tiny for this small static asset.
SIZE = 512
rng = np.random.default_rng(20260908)
noise = rng.normal(0.0, 1.0, (SIZE, SIZE)).astype(np.float32)
for _ in range(4):
    noise = (noise + np.roll(noise, 1, 0) + np.roll(noise, -1, 0) + np.roll(noise, 1, 1) + np.roll(noise, -1, 1)) / 5.0
noise = np.clip(noise * 0.13, -0.12, 0.12)
yy, _xx = np.mgrid[0:SIZE, 0:SIZE]

base = np.empty((SIZE, SIZE, 4), dtype=np.float32)
steel_green = np.asarray([0.285, 0.315, 0.205], dtype=np.float32)
base[..., :3] = np.clip(steel_green * (1.0 + noise[..., None]), 0.0, 1.0)
base[..., 3] = 1.0
# Sparse restrained rust/grime, heavier at the lower portion.
spots = (rng.random((SIZE, SIZE)) > 0.997) | ((yy > SIZE * 0.80) & (rng.random((SIZE, SIZE)) > 0.994))
base[..., 0][spots] = np.clip(base[..., 0][spots] + 0.20, 0.0, 1.0)
base[..., 1][spots] = np.clip(base[..., 1][spots] - 0.06, 0.0, 1.0)
base[..., 2][spots] = np.clip(base[..., 2][spots] - 0.08, 0.0, 1.0)

# DCS RoughMet: R=AO, G=roughness, B=metalness.
rmo = np.empty((SIZE, SIZE, 4), dtype=np.float32)
rmo[..., 0] = np.clip(0.94 - np.maximum(noise, 0.0) * 0.12, 0.82, 1.0)
rmo[..., 1] = np.clip(0.72 + noise * 0.35, 0.48, 0.92)
rmo[..., 2] = 0.08
rmo[..., 3] = 1.0

normal = np.empty((SIZE, SIZE, 4), dtype=np.float32)
gx = np.gradient(noise, axis=1)
gy = np.gradient(noise, axis=0)
normal[..., 0] = np.clip(0.5 + gx * 0.025, 0.0, 1.0)
normal[..., 1] = np.clip(0.5 + gy * 0.025, 0.0, 1.0)
normal[..., 2] = 1.0
normal[..., 3] = 1.0


def save_image(name: str, pixels: np.ndarray, non_color: bool = False):
    img = bpy.data.images.new(name, width=SIZE, height=SIZE, alpha=True, float_buffer=False)
    img.pixels.foreach_set(pixels.reshape(-1))
    if non_color:
        try:
            img.colorspace_settings.name = 'Non-Color'
        except Exception:
            pass
    img.file_format = 'PNG'
    path = ART / f'{name}.png'
    img.filepath_raw = str(path)
    img.save()
    return img, path


base_img, base_path = save_image('TPG_Container_Base', base)
rmo_img, rmo_path = save_image('TPG_Container_RoughMet', rmo, True)
normal_img, normal_path = save_image('TPG_Container_Normal', normal, True)

# Official Eagle Dynamics default PBR material.
mat = bpy.data.materials.new('TPG_Container_EDM_PBR')
mat.use_nodes = True
mat.node_tree.nodes.clear()
descriptions = build_material_descriptions()
desc = descriptions.get(DefaultMaterial.name)
if desc is None:
    raise RuntimeError('Official ED Default Material description unavailable')
edm_node = mat.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
edm_node.post_init(desc)
edm_node.name = 'TPG_Container_EDM_Default'


def bind(socket_name: str, img):
    socket = edm_node.inputs.get(socket_name)
    if socket is None:
        raise RuntimeError(f'ED material socket missing: {socket_name}')
    tex = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Linear'
    mat.node_tree.links.new(tex.outputs['Color'], socket)


bind('Base Color', base_img)
bind('RoughMet (Non-Color)', rmo_img)
bind('Normal (Non-Color)', normal_img)
alpha = edm_node.inputs.get('Base Alpha*')
if alpha is not None:
    alpha.default_value = 1.0
render.data.materials.clear()
render.data.materials.append(mat)

# Very cheap collision for the closed container body only. The open doors remain visual.
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 1.2875))
collision = bpy.context.object
collision.name = 'TPG_10FT_CONTAINER_OPEN_LITE_COLLISION'
collision.dimensions = (3.145, 2.425, 2.575)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
collision.data.materials.clear()
collision.EDMProps.SPECIAL_TYPE = 'COLLISION_SHELL'

# Hard QA gates: fail instead of exporting a wrong-scale or bloated asset.
bpy.context.view_layer.update()
world = np.asarray([tuple(render.matrix_world @ v.co) for v in render.data.vertices], dtype=np.float64)
extents = world.max(axis=0) - world.min(axis=0)
min_z = float(world[:, 2].min())
triangles = sum(max(0, len(p.vertices) - 2) for p in render.data.polygons)
if triangles != 14999:
    raise RuntimeError(f'Wrong optimized triangle count: {triangles}')
if not (3.10 <= extents[0] <= 3.20 and 5.05 <= extents[1] <= 5.20 and 2.55 <= extents[2] <= 2.63):
    raise RuntimeError(f'Bad DCS orientation/scale extents: {tuple(extents)}')
if abs(min_z) > 0.001:
    raise RuntimeError(f'Model not grounded: minZ={min_z}')
if collision.EDMProps.SPECIAL_TYPE != 'COLLISION_SHELL':
    raise RuntimeError('Collision shell EDM flag failed')

render['TPG_DCS_ASSET'] = 'TPG_10FT_CONTAINER_OPEN_LITE_V1'
render['TPG_SOURCE_TRIANGLES'] = 715802
render['TPG_GAME_TRIANGLES'] = triangles
render['TPG_COMPACT_PAYLOAD_CHARS'] = len(encoded)
print(f'[TPG CONTAINER] payload={len(encoded)} chars raw={len(raw)} bytes')
print(f'[TPG CONTAINER] vertices={vertex_count} triangles={triangles}')
print(f'[TPG CONTAINER] extents={tuple(round(float(x), 6) for x in extents)} minZ={min_z:.6f}')
print(f'[TPG CONTAINER] textures={base_path.name},{rmo_path.name},{normal_path.name}')
