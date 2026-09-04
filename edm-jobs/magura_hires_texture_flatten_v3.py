import os
from pathlib import Path

import bpy
import numpy as np

# V3 texture correction for the DCS close-up QA issue: the procedural hull normal
# was too strong/directional and became obvious as repeated wrinkles around the
# stern and other curved hull radii. Preserve only a tiny amount of micro-normal
# character and blend the rest toward a flat tangent-space normal.

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
TEXDIR = ROOT / "hires-generated" / "textures"
NAME = "MAGURA_W6_Hull_Normal_HiRes"
PATH = TEXDIR / "MAGURA_W6_Hull_Normal_HiRes.png"

img = bpy.data.images.get(NAME)
if img is None:
    # Core visual patch should already have loaded it, but support direct load.
    if not PATH.exists():
        raise RuntimeError(f"Hull normal texture missing: {PATH}")
    img = bpy.data.images.load(str(PATH), check_existing=False)
    img.name = NAME

w, h = img.size
count = w * h * 4
pixels = np.empty(count, dtype=np.float32)
img.pixels.foreach_get(pixels)
a = pixels.reshape((h, w, 4))

# 6% of the old microdetail, 94% flat normal. This removes the visibly periodic
# ribbing on curved surfaces while retaining enough microvariation to avoid a
# totally synthetic flat-plastic response.
keep = 0.06
a[:, :, 0] = a[:, :, 0] * keep + 0.5 * (1.0 - keep)
a[:, :, 1] = a[:, :, 1] * keep + 0.5 * (1.0 - keep)
a[:, :, 2] = a[:, :, 2] * keep + 1.0 * (1.0 - keep)
a[:, :, 3] = 1.0
img.pixels.foreach_set(pixels)
img.update()
img.filepath_raw = str(PATH)
img.file_format = "PNG"
img.save()

print(f"MAGURA_HIRES_V3_HULL_NORMAL_FLATTENED=1 size={w}x{h} keep={keep}")
