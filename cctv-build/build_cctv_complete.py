from __future__ import annotations
import os
import runpy
from pathlib import Path

ROOT = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
SRC_DIR = (ROOT / 'cctv-build' / 'source').resolve()
PAYLOAD = SRC_DIR / 'complete_payload.b64'
TARGET = ROOT / 'cctv-build' / 'build_cctv.py'

if not PAYLOAD.exists():
    raise FileNotFoundError(f'Complete CCTV payload missing: {PAYLOAD}')

expected_chars = 252560
text = PAYLOAD.read_text(encoding='ascii').strip()
if len(text) != expected_chars:
    raise RuntimeError(f'Complete CCTV payload length mismatch: {len(text)} != {expected_chars}')

# Reuse the already-vetted build script unchanged, but make its historical
# part_*.b64 lookup resolve exclusively to the verified complete payload.
_original_glob = Path.glob

def _cctv_glob(self, pattern):
    if self.resolve() == SRC_DIR and pattern == 'part_*.b64':
        return iter([PAYLOAD])
    return _original_glob(self, pattern)

Path.glob = _cctv_glob
try:
    print(f'[CCTV] Using verified complete payload: {PAYLOAD} ({len(text)} base64 chars)')
    runpy.run_path(str(TARGET), run_name='__main__')
finally:
    Path.glob = _original_glob
