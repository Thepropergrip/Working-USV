from __future__ import annotations
import os
import runpy
from pathlib import Path

ROOT = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
print('[TPG CONTAINER] starting verified compact-mesh native EDM build')
runpy.run_path(str(ROOT / 'edm-jobs' / 'build_tpg_container_lite.py'), run_name='__main__')
