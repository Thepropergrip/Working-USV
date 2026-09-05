import json
import os
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
OUT = ROOT / "magura-material-audit.json"

focus_tokens = ("Hull", "HULL", "Deck", "DECK", "Fairing", "Bow", "Panel", "Hatch", "Armor")
rows = []

for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    if not any(tok in obj.name for tok in focus_tokens):
        continue
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    center = [(mn[i] + mx[i]) * 0.5 for i in range(3)]
    dims = [mx[i] - mn[i] for i in range(3)]
    mats = [slot.material.name if slot.material else None for slot in obj.material_slots]
    poly_counts = {}
    for poly in obj.data.polygons:
        idx = poly.material_index
        name = mats[idx] if 0 <= idx < len(mats) else None
        poly_counts[name] = poly_counts.get(name, 0) + 1
    rows.append({
        "name": obj.name,
        "collections": [c.name for c in obj.users_collection],
        "center": [round(float(v), 5) for v in center],
        "dims": [round(float(v), 5) for v in dims],
        "materials": mats,
        "polygon_material_counts": poly_counts,
    })

rows.sort(key=lambda x: x["name"])
OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print("MAGURA_MATERIAL_AUDIT_BEGIN")
print(json.dumps(rows, indent=2))
print("MAGURA_MATERIAL_AUDIT_END")
