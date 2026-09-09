from __future__ import annotations
import os
import runpy
from pathlib import Path

ROOT = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
PARTDIR = ROOT / 'container-build-payload'
TARGET = PARTDIR / 'model_b64.txt'
parts = sorted(PARTDIR.glob('part*.txt'))
if not parts:
    raise FileNotFoundError(f'No container payload parts found in {PARTDIR}')
TARGET.write_text(''.join(p.read_text(encoding='ascii').strip() for p in parts), encoding='ascii')
print(f'[TPG CONTAINER] concatenated {len(parts)} payload parts -> {TARGET} ({TARGET.stat().st_size} chars)')
runpy.run_path(str(ROOT / 'edm-jobs' / 'build_tpg_container_lite.py'), run_name='__main__')
