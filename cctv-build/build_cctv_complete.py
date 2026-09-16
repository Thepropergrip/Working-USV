from __future__ import annotations
import hashlib
import os
import runpy
from pathlib import Path

ROOT = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
SRC_DIR = (ROOT / 'cctv-build' / 'source').resolve()
TARGET = ROOT / 'cctv-build' / 'build_cctv.py'

# The complete CCTV payload is stored as 16 small shards because the connector
# path used to stage one large text blob truncates it. Two historical shard
# writes contain accidental trailing characters; only the exact expected prefix
# of each shard is authoritative.
parts = sorted(SRC_DIR.glob('payload16_*.b64'))
if len(parts) != 16:
    raise RuntimeError(f'Expected 16 CCTV payload shards, found {len(parts)}: {[p.name for p in parts]}')

chunks = []
for i, p in enumerate(parts):
    raw = p.read_text(encoding='ascii').strip()
    expected = 12560 if i == 15 else 16000
    if len(raw) < expected:
        raise RuntimeError(f'CCTV shard {p.name} is short: {len(raw)} < {expected}')
    if len(raw) != expected:
        print(f'[CCTV] Trimming known staging tail from {p.name}: {len(raw)} -> {expected}')
    chunks.append(raw[:expected])

text = ''.join(chunks)
expected_chars = 252560
expected_sha256 = '06cf9fcaa6f89305caada13bb10bf7d584c53e7464a995620d8b8c709ce0744c'
if len(text) != expected_chars:
    raise RuntimeError(f'CCTV shard payload length mismatch: {len(text)} != {expected_chars}')
actual_sha256 = hashlib.sha256(text.encode('ascii')).hexdigest()
if actual_sha256 != expected_sha256:
    raise RuntimeError(f'CCTV payload SHA256 mismatch: {actual_sha256} != {expected_sha256}')

# Reuse the vetted build script unchanged. It historically asks for part_*.b64;
# expose sanitized temporary shard files for that one lookup.
sanitized_dir = ROOT / 'cctv-build' / '_sanitized_payload'
sanitized_dir.mkdir(parents=True, exist_ok=True)
sanitized = []
for i, chunk in enumerate(chunks):
    p = sanitized_dir / f'part_{i:03d}.b64'
    p.write_text(chunk, encoding='ascii')
    sanitized.append(p)

_original_glob = Path.glob

def _cctv_glob(self, pattern):
    if self.resolve() == SRC_DIR and pattern == 'part_*.b64':
        return iter(sanitized)
    return _original_glob(self, pattern)

Path.glob = _cctv_glob
try:
    print(f'[CCTV] Verified 16-shard payload: {len(text)} chars, SHA256={actual_sha256}')
    runpy.run_path(str(TARGET), run_name='__main__')
finally:
    Path.glob = _original_glob
