"""Audit only. Does not modify the approved Grizzly model or animation."""
import bpy, hashlib, json, os, urllib.request
from pathlib import Path
from mathutils import Vector

out = Path(os.environ['GITHUB_WORKSPACE']) / 'edm-artifacts'
out.mkdir(parents=True, exist_ok=True)
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
records = []
for obj in bpy.data.objects:
    item = {'name': obj.name, 'type': obj.type,
            'parent': obj.parent.name if obj.parent else None,
            'collections': [c.name for c in obj.users_collection],
            'location': list(obj.location), 'rotation': list(obj.rotation_euler),
            'scale': list(obj.scale),
            'action': obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None}
    if obj.type == 'MESH':
        pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
        item['bounds'] = [[min(v[i] for v in pts), max(v[i] for v in pts)] for i in range(3)]
        item['vertices'] = len(pts)
        item['materials'] = [m.name if m else None for m in obj.data.materials]
    records.append(item)
(out / 'grizzly_object_audit.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
print('GRIZZLY_AUDIT_OBJECTS', len(records))
# Acquire the matching official Linux viewer/render build for the offline
# validation workspace. This is tooling, never part of the user's Tech ZIP.
url = 'https://download.blender.org/release/Blender4.1/blender-4.1.1-linux-x64.tar.xz'
path = out / 'blender-4.1.1-linux-x64.tar.xz'
print('ACQUIRE_OFFLINE_RENDER_TOOL', url, flush=True)
with urllib.request.urlopen(url, timeout=120) as response, path.open('wb') as handle:
    while True:
        block = response.read(4 * 1024 * 1024)
        if not block:
            break
        handle.write(block)
if path.stat().st_size != 297954552:
    raise RuntimeError('Unexpected size for the pinned official Blender Linux build')
print('OFFLINE_RENDER_TOOL_READY', path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest(), flush=True)
