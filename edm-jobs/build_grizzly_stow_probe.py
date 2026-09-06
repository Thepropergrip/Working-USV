import os, runpy, sys, tarfile, tempfile
from pathlib import Path
import bpy

workspace = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
archive = workspace / 'edm-jobs' / 'grizzly_rc4_scripts.tgz'
root = Path(tempfile.mkdtemp(prefix='grizzly_stow_probe_'))
with tarfile.open(archive, mode='r:gz') as tf:
    tf.extractall(root)

# Same Blender 4.1.1 UV compatibility patch used by the proven RC4 build.
model_path = root / '02_model.py'
model = model_path.read_text(encoding='utf-8')
old_uv = '''    bpy.ops.object.modifier_apply(modifier=solid.name); bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    grizzly_release_uv(obj)
    bpy.ops.object.mode_set(mode="OBJECT")
'''
new_uv = '''    bpy.ops.object.modifier_apply(modifier=solid.name); bpy.ops.object.modifier_apply(modifier=bevel.name)
    grizzly_release_uv(obj)
'''
if old_uv not in model:
    raise RuntimeError('Expected original GRIZZLY UV block not found')
model_path.write_text(model.replace(old_uv, new_uv), encoding='utf-8')

sys.path.insert(0, str(root))
for stage in ('01_scene_setup.py','02_model.py','03_materials.py','04_connectors_and_animation.py'):
    print(f'[GRIZZLY STOW PROBE] running {stage}')
    runpy.run_path(str(root / stage), run_name='__main__')

from grizzly_common import DESTROYED_LODS, INTACT_LODS, SUPPORT_COLLECTIONS, set_collection_visible
for name in INTACT_LODS + SUPPORT_COLLECTIONS:
    set_collection_visible(name, True)
for name in DESTROYED_LODS:
    set_collection_visible(name, False)

print('=== GRIZZLY SOURCE OBJECT PROBE BEGIN ===')
keywords = ('GRIZZLY','POINT','LID','DOOR','HATCH','COVER','LAUNCH','VLS','RAIL','MISSILE','ROOF','TOP')
for obj in sorted(bpy.data.objects, key=lambda o: o.name):
    if any(k in obj.name.upper() for k in keywords):
        parent = obj.parent.name if obj.parent else '-'
        cols = ','.join(c.name for c in obj.users_collection)
        ad = obj.animation_data
        action = ad.action.name if ad and ad.action else '-'
        loc = obj.location
        dims = obj.dimensions
        print(f'OBJ|{obj.name}|type={obj.type}|parent={parent}|loc=({loc.x:.4f},{loc.y:.4f},{loc.z:.4f})|dims=({dims.x:.4f},{dims.y:.4f},{dims.z:.4f})|action={action}|collections={cols}')

print('=== ACTIONS ===')
for action in sorted(bpy.data.actions, key=lambda a: a.name):
    print(f'ACTION|{action.name}|frames={tuple(action.frame_range)}|fcurves={len(action.fcurves)}')
print('=== COLLECTIONS ===')
for coll in sorted(bpy.data.collections, key=lambda c: c.name):
    print(f'COLLECTION|{coll.name}|objects={len(coll.objects)}|children={len(coll.children)}')
print('=== GRIZZLY SOURCE OBJECT PROBE END ===')

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print('[GRIZZLY STOW PROBE] scene ready for export')
