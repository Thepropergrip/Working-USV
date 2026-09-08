from __future__ import annotations

import base64
import lzma
import math
import os
from pathlib import Path

import bpy
import numpy as np
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
PAYLOAD = ROOT / "container-build-payload" / "model_b64.txt"
ART = ROOT / "edm-artifacts"
ART.mkdir(parents=True, exist_ok=True)
TMP = ART / "TPG_10FT_CONTAINER_15K.obj"

if not PAYLOAD.exists():
    raise FileNotFoundError(f"Missing optimized model payload: {PAYLOAD}")
raw = lzma.decompress(base64.b64decode(PAYLOAD.read_text(encoding="ascii").strip()))
TMP.write_bytes(raw)

# Import the already optimized, correctly oriented, meter-scale mesh.
bpy.ops.wm.obj_import(filepath=str(TMP))
render = bpy.context.selected_objects[0]
render.name = "TPG_10FT_CONTAINER_MODULE_RENDER"

# Put origin at the body's XY center and ground the lowest point exactly at Z=0.
bpy.context.view_layer.objects.active = render
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
coords = [render.matrix_world @ v.co for v in render.data.vertices]
minx, maxx = min(v.x for v in coords), max(v.x for v in coords)
miny, maxy = min(v.y for v in coords), max(v.y for v in coords)
minz = min(v.z for v in coords)
render.location.x -= (minx + maxx) * 0.5
render.location.y -= (miny + maxy) * 0.5
render.location.z -= minz
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Compact UV unwrap. Geometry carries the corrugations; texture adds painted-steel character.
bpy.context.view_layer.objects.active = render
render.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')

# Generate compact 1024 PBR maps. No giant source textures are needed.
SIZE = 1024
rng = np.random.default_rng(20260908)
yy, xx = np.mgrid[0:SIZE, 0:SIZE]
noise = rng.normal(0.0, 1.0, (SIZE, SIZE)).astype(np.float32)
# low-frequency grime by repeated neighborhood smoothing
for _ in range(5):
    noise = (noise + np.roll(noise,1,0) + np.roll(noise,-1,0) + np.roll(noise,1,1) + np.roll(noise,-1,1)) / 5.0
noise = np.clip(noise * 0.18, -0.16, 0.16)

base_rgb = np.array([0.285, 0.315, 0.205], dtype=np.float32)
base_arr = np.zeros((SIZE, SIZE, 4), dtype=np.float32)
base_arr[..., :3] = np.clip(base_rgb[None,None,:] * (1.0 + noise[...,None]), 0, 1)
base_arr[..., 3] = 1.0
# restrained warm edge/rust freckles, mostly near lower quarter and random sparse spots
rust = ((rng.random((SIZE,SIZE)) > 0.996) | ((yy > SIZE*0.78) & (rng.random((SIZE,SIZE)) > 0.992)))
base_arr[rust,0] = np.clip(base_arr[rust,0] + 0.22, 0, 1)
base_arr[rust,1] = np.clip(base_arr[rust,1] - 0.08, 0, 1)
base_arr[rust,2] = np.clip(base_arr[rust,2] - 0.10, 0, 1)

# DCS RoughMet convention: R=roughness, G=metalness, B=AO.
rmo_arr = np.zeros((SIZE, SIZE, 4), dtype=np.float32)
rmo_arr[...,0] = np.clip(0.68 + noise*0.45, 0.45, 0.92)
rmo_arr[...,1] = 0.18
rmo_arr[...,2] = np.clip(0.94 - np.maximum(noise,0)*0.15, 0.78, 1.0)
rmo_arr[...,3] = 1.0

# Flat tangent-space normal with tiny fine-steel variation; modeled corrugation supplies macro normals.
normal_arr = np.zeros((SIZE,SIZE,4), dtype=np.float32)
normal_arr[...,0] = np.clip(0.5 + np.gradient(noise, axis=1)*0.03, 0, 1)
normal_arr[...,1] = np.clip(0.5 + np.gradient(noise, axis=0)*0.03, 0, 1)
normal_arr[...,2] = 1.0
normal_arr[...,3] = 1.0

def save_image(name, arr, non_color=False):
    img = bpy.data.images.new(name, width=SIZE, height=SIZE, alpha=True, float_buffer=False)
    img.pixels.foreach_set(arr.reshape(-1))
    img.file_format = 'PNG'
    path = ART / f"{name}.png"
    img.filepath_raw = str(path)
    img.save()
    if non_color:
        try: img.colorspace_settings.name = 'Non-Color'
        except Exception: pass
    return img, path

base_img, base_path = save_image("TPG_Container_Base", base_arr)
rmo_img, rmo_path = save_image("TPG_Container_RoughMet", rmo_arr, True)
normal_img, normal_path = save_image("TPG_Container_Normal", normal_arr, True)

# Native ED default PBR material.
mat = bpy.data.materials.new("TPG_Container_EDM_PBR")
mat.use_nodes = True
mat.node_tree.nodes.clear()
descs = build_material_descriptions()
desc = descs.get(DefaultMaterial.name)
if desc is None:
    raise RuntimeError("Official ED Default Material description unavailable")
edm_node = mat.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
edm_node.post_init(desc)
edm_node.name = "TPG_Container_EDM_Default"

# Bind actual texture image nodes into the ED sockets.
def bind(sock_name, img):
    sock = edm_node.inputs.get(sock_name)
    if sock is None:
        raise RuntimeError(f"ED material missing socket: {sock_name}")
    tex = mat.node_tree.nodes.new(type="ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = 'Linear'
    mat.node_tree.links.new(tex.outputs['Color'], sock)

bind("Base Color", base_img)
bind("RoughMet (Non-Color)", rmo_img)
bind("Normal (Non-Color)", normal_img)
if edm_node.inputs.get("Base Alpha*"):
    edm_node.inputs["Base Alpha*"].default_value = 1.0
render.data.materials.clear()
render.data.materials.append(mat)

# Ultra-light collision shell for the closed container body only; open doors do not inflate physics cost.
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 1.275))
collision = bpy.context.object
collision.name = "TPG_10FT_CONTAINER_MODULE_COLLISION"
collision.dimensions = (3.12, 2.54, 2.55)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
collision.data.materials.clear()
collision.EDMProps.SPECIAL_TYPE = "COLLISION_SHELL"

# QA gate: reject bad scale/orientation or accidental CAD-density regression.
triangles = sum(max(0, len(p.vertices)-2) for p in render.data.polygons)
coords = [render.matrix_world @ v.co for v in render.data.vertices]
extents = (
    max(v.x for v in coords)-min(v.x for v in coords),
    max(v.y for v in coords)-min(v.y for v in coords),
    max(v.z for v in coords)-min(v.z for v in coords),
)
min_z = min(v.z for v in coords)
if not (14000 <= triangles <= 16000):
    raise RuntimeError(f"Unexpected triangle count: {triangles}")
if not (3.0 <= extents[0] <= 3.3 and 5.0 <= extents[1] <= 5.3 and 2.5 <= extents[2] <= 2.7):
    raise RuntimeError(f"Bad DCS orientation/scale extents: {extents}")
if abs(min_z) > 0.003:
    raise RuntimeError(f"Model is not grounded: minZ={min_z}")
if collision.EDMProps.SPECIAL_TYPE != "COLLISION_SHELL":
    raise RuntimeError("Collision shell flag failed")

render["TPG_SOURCE_TRIANGLES"] = 715802
render["TPG_GAME_TRIANGLES"] = triangles
render["TPG_DCS_ASSET"] = "TPG_10FT_CONTAINER_MODULE_LITE"
print(f"[TPG CONTAINER] triangles={triangles} extents={extents} minZ={min_z:.6f}")
print(f"[TPG CONTAINER] textures={base_path.name},{rmo_path.name},{normal_path.name}")
