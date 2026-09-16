from __future__ import annotations
import os
import runpy
from pathlib import Path

ROOT = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
SRC_DIR = (ROOT / 'cctv-build' / 'source').resolve()
TARGET = ROOT / 'cctv-build' / 'build_cctv.py'

# The complete CCTV payload is intentionally stored as 16 small shards because
# the connector/API path used to stage one large text blob truncates it.
parts = sorted(SRC_DIR.glob('payload16_*.b64'))
if len(parts) != 16:
    raise RuntimeError(f'Expected 16 CCTV payload shards, found {len(parts)}: {[p.name for p in parts]}')

expected_chars = 252560
text = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
if len(text) != expected_chars:
    raise RuntimeError(f'CCTV shard payload length mismatch: {len(text)} != {expected_chars}')

# Reuse the vetted build script unchanged. It historically asks for part_*.b64;
# redirect that one lookup to the verified payload16 shard set.
_original_glob = Path.glob

def _cctv_glob(self, pattern):
    if self.resolve() == SRC_DIR and pattern == 'part_*.b64':
        return iter(parts)
    return _original_glob(self, pattern)

Path.glob = _cctv_glob
try:
    print(f'[CCTV] Using {len(parts)} verified payload shards ({len(text)} base64 chars)')
    runpy.run_path(str(TARGET), run_name='__main__')
finally:
    Path.glob = _original_glob
