import os, runpy, sys, tarfile, tempfile
from pathlib import Path
import bpy

workspace = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
archive = workspace / 'edm-jobs' / 'grizzly_rc4_scripts.tgz'
root = Path(tempfile.mkdtemp(prefix='grizzly_rc4_'))
with tarfile.open(archive, mode='r:gz') as tf:
    tf.extractall(root)
sys.path.insert(0, str(root))
for stage in ('01_scene_setup.py','02_model.py','03_materials.py','04_connectors_and_animation.py'):
    print(f'[GRIZZLY RC4] running {stage}')
    runpy.run_path(str(root / stage), run_name='__main__')

from grizzly_common import DESTROYED_LODS, INTACT_LODS, SUPPORT_COLLECTIONS, set_collection_visible
for name in INTACT_LODS + SUPPORT_COLLECTIONS:
    set_collection_visible(name, True)
for name in DESTROYED_LODS:
    set_collection_visible(name, False)
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

for i in range(1, 9):
    conn = bpy.data.objects.get(f'POINT_GRIZZLY_{i:02d}')
    pivot = bpy.data.objects.get(f'GRIZZLY_VLS_YAW_{i:02d}')
    if conn is None or pivot is None or conn.parent != pivot:
        raise RuntimeError(f'Invalid RC4 VLS cell {i}')
    if abs(conn.matrix_world.translation.z - 2.84) > 1e-4:
        raise RuntimeError(f'Connector {i} wrong Z: {conn.matrix_world.translation.z}')
    if not pivot.animation_data or not pivot.animation_data.action:
        raise RuntimeError(f'Pivot {i} missing DCS argument-0 animation')
print('[GRIZZLY RC4] validated 8 target-relative VLS pivots at Z=2.84m')
