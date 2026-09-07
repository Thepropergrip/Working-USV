from pathlib import Path
import bpy, os

# Build script placeholder intentionally fails if the packed source payload has not been staged.
# This prevents the workflow from silently exporting a substitute or simplified mesh.
root = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd()))
payload = root / 'edm-jobs' / 'cgaxr_mc_drone' / 'source_payload.txt'
if not payload.exists():
    raise FileNotFoundError('Full-resolution CGAXR source payload is not staged; refusing to export a placeholder model.')

# The payload decoder/reconstruction routine is generated alongside source_payload.txt.
exec((root / 'edm-jobs' / 'cgaxr_mc_drone' / 'reconstruct_source.py').read_text(encoding='utf-8'), globals(), globals())
