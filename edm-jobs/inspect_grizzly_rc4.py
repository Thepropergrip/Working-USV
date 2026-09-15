import os, tarfile, tempfile
from pathlib import Path
import bpy

workspace = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
archive = workspace / 'edm-jobs' / 'grizzly_rc4_scripts.tgz'
root = Path(tempfile.mkdtemp(prefix='grizzly_inspect_'))
with tarfile.open(archive, mode='r:gz') as tf:
    tf.extractall(root)

for name in ('01_scene_setup.py','02_model.py','03_materials.py','04_connectors_and_animation.py','grizzly_common.py'):
    p = root / name
    print(f'===== BEGIN {name} =====')
    print(p.read_text(encoding='utf-8'))
    print(f'===== END {name} =====')

# Keep the normal EDM job runner satisfied.
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0,0,0))
bpy.context.object.name = 'GRIZZLY_SOURCE_INSPECTION_DUMMY'
