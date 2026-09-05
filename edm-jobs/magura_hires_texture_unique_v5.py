import json
import os
import shutil
from pathlib import Path

import bpy

# V5 coexistence rule: every modified HiRes texture gets a V5-specific filename
# before EDM export so installing V5 beside HiRes/V2/V3/V4 cannot silently change
# another variant through DCS's global VFS texture lookup.

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
TEXDIR = ROOT / "hires-generated" / "textures"
REPORT = ROOT / "hires-generated" / "visual-qa.json"

RENAME = {
    "MAGURA_W6_Hull_Base_HiRes.png": "MAGURA_W6_Hull_Base_HiRes_V5.png",
    "MAGURA_W6_Hull_Normal_HiRes.png": "MAGURA_W6_Hull_Normal_HiRes_V5.png",
    "MAGURA_W6_Hull_RoughMet_HiRes.png": "MAGURA_W6_Hull_RoughMet_HiRes_V5.png",
    "MAGURA_W6_Deck_Base_HiRes.png": "MAGURA_W6_Deck_Base_HiRes_V5.png",
    "MAGURA_W6_Deck_RoughMet_HiRes.png": "MAGURA_W6_Deck_RoughMet_HiRes_V5.png",
    "MAGURA_W6_Metal_Base_HiRes.png": "MAGURA_W6_Metal_Base_HiRes_V5.png",
    "MAGURA_W6_Metal_RoughMet_HiRes.png": "MAGURA_W6_Metal_RoughMet_HiRes_V5.png",
    "MAGURA_W6_Armor_Base_HiRes.png": "MAGURA_W6_Armor_Base_HiRes_V5.png",
    "MAGURA_W6_Armor_RoughMet_HiRes.png": "MAGURA_W6_Armor_RoughMet_HiRes_V5.png",
    "MAGURA_W6_Optics_Base_HiRes.png": "MAGURA_W6_Optics_Base_HiRes_V5.png",
    "MAGURA_W6_Optics_RoughMet_HiRes.png": "MAGURA_W6_Optics_RoughMet_HiRes_V5.png",
    "MAGURA_W6_Glass_Filter_HiRes.png": "MAGURA_W6_Glass_Filter_HiRes_V5.png",
    "MAGURA_W6_Damage_Base_HiRes.png": "MAGURA_W6_Damage_Base_HiRes_V5.png",
}

copied = []
for old_name, new_name in RENAME.items():
    src = TEXDIR / old_name
    dst = TEXDIR / new_name
    if not src.exists():
        raise RuntimeError(f"V5 coexist texture source missing: {src}")
    shutil.copy2(src, dst)
    copied.append(new_name)

# Repoint all Blender image datablocks that use one of the modified HiRes files.
# Nodes retain the same image object, so changing the image filepath/name changes
# the texture reference exported into the EDM without altering material behavior.
repointed = []
for img in bpy.data.images:
    try:
        basename = Path(bpy.path.abspath(img.filepath)).name
    except Exception:
        basename = Path(img.filepath).name if img.filepath else ""
    if basename not in RENAME:
        continue
    new_name = RENAME[basename]
    new_path = TEXDIR / new_name
    img.filepath = str(new_path)
    img.filepath_raw = str(new_path)
    img.name = Path(new_name).stem
    repointed.append({"from": basename, "to": new_name})

# Hard QA: every modified filename that is still referenced by a material image
# node would break coexistence, so fail the export if any old name survives.
old_refs = []
for mat in bpy.data.materials:
    if not mat.use_nodes or not mat.node_tree:
        continue
    for node in mat.node_tree.nodes:
        img = getattr(node, "image", None)
        if img is None:
            continue
        try:
            basename = Path(bpy.path.abspath(img.filepath)).name
        except Exception:
            basename = Path(img.filepath).name if img.filepath else ""
        if basename in RENAME:
            old_refs.append({"material": mat.name, "texture": basename})

if old_refs:
    raise RuntimeError(f"V5 coexistence failed: old modified texture refs remain: {old_refs}")

report = {}
if REPORT.exists():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
report["coexistence_v5_textures"] = {
    "status": "success",
    "policy": "all modified HiRes texture files receive V5-specific basenames before EDM export",
    "renamed_files": RENAME,
    "copied_v5_files": copied,
    "repointed_images": repointed,
    "old_modified_texture_refs_remaining": old_refs,
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("MAGURA_HIRES_V5_TEXTURE_COEXIST_READY=1")
print(json.dumps(report["coexistence_v5_textures"], indent=2))
