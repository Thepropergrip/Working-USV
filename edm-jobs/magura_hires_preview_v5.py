import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
OUT = ROOT / "hires-generated" / "preview-v5"
OUT.mkdir(parents=True, exist_ok=True)
LOD0 = "MAGURA_LOD_0_90"

# Headless-safe QA preview generator. Do NOT invoke Blender render engines here:
# GitHub's Windows runner has no usable OpenGL context. Instead, project the
# actual world-space mesh bounding boxes into SVG views. This is sufficient for
# checking detached/floating placement and cannot crash the EDM export process.


def in_lod0(obj):
    return any(c.name == LOD0 for c in obj.users_collection)


def corners_world(obj):
    return [obj.matrix_world @ Vector(c) for c in obj.bound_box]


def dims_world(pts):
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))


def project(p, view):
    if view == "top":
        return (p.x, p.y)
    if view == "starboard":
        return (p.x, p.z)
    if view == "front":
        return (p.y, p.z)
    # Axonometric: readable front-starboard geometry layout.
    return (p.x - 0.55 * p.y, p.z + 0.22 * p.y)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


objects = []
for obj in bpy.data.objects:
    if obj.type != "MESH" or not in_lod0(obj):
        continue
    pts = corners_world(obj)
    dims = dims_world(pts)
    center = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)
    objects.append({
        "name": obj.name,
        "corners": [[float(p.x), float(p.y), float(p.z)] for p in pts],
        "dims": [float(v) for v in dims],
        "center": [float(center.x), float(center.y), float(center.z)],
        "small": max(dims) <= 0.35,
    })

(OUT / "object-layout-v5.json").write_text(json.dumps(objects, indent=2), encoding="utf-8")

for view in ("top", "starboard", "front", "axonometric"):
    projected = []
    for item in objects:
        ps = [project(Vector(p), view) for p in item["corners"]]
        xs = [p[0] for p in ps]
        ys = [p[1] for p in ps]
        projected.append((item, min(xs), max(xs), min(ys), max(ys)))

    xmin = min(v[1] for v in projected) - 0.3
    xmax = max(v[2] for v in projected) + 0.3
    ymin = min(v[3] for v in projected) - 0.3
    ymax = max(v[4] for v in projected) + 0.3
    W, H = 1400, 1000
    sx = W / max(1e-6, xmax - xmin)
    sy = H / max(1e-6, ymax - ymin)
    scale = min(sx, sy) * 0.92
    ox = (W - (xmax - xmin) * scale) * 0.5
    oy = (H - (ymax - ymin) * scale) * 0.5

    def xy(x, y):
        px = ox + (x - xmin) * scale
        py = H - (oy + (y - ymin) * scale)
        return px, py

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        '<rect width="100%" height="100%" fill="#11161b"/>',
        f'<text x="24" y="38" fill="#ffffff" font-family="monospace" font-size="24">MAGURA V5 geometry QA — {view}</text>',
    ]

    # Draw larger structural objects first, then small objects on top.
    for item, x0, x1, y0, y1 in sorted(projected, key=lambda v: v[0]["small"]):
        px0, py1 = xy(x0, y0)
        px1, py0 = xy(x1, y1)
        w = max(1.0, px1 - px0)
        h = max(1.0, py1 - py0)
        if item["small"]:
            stroke = "#ffb000"
            fill = "#ffb00022"
            sw = 2.0
        else:
            stroke = "#92a4b4"
            fill = "#92a4b40f"
            sw = 1.0
        lines.append(f'<rect x="{px0:.2f}" y="{py0:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        if item["small"]:
            cx, cy = xy((x0+x1)*0.5, (y0+y1)*0.5)
            lines.append(f'<text x="{cx+4:.2f}" y="{cy-4:.2f}" fill="#ffd36a" font-family="monospace" font-size="11">{esc(item["name"])}</text>')

    lines.append('</svg>')
    path = OUT / f"{view}.svg"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"MAGURA_V5_PREVIEW={path}")

print("MAGURA_HIRES_V5_PREVIEWS_READY=1")
