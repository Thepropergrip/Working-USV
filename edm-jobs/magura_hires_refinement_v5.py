import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

# MAGURA HiRes V5 corrective pass.
# Purpose: remove genuinely detached visual parts and snap small decorative
# attachments flush to the surfaces they were visibly hovering above in DCS.
# VISUAL ONLY: no Lua, connectors, weapon/sensor data, animation arguments or
# protected pivot transforms are changed.

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
REPORT = ROOT / "hires-generated" / "visual-qa.json"
LOD0 = "MAGURA_LOD_0_90"

PROTECTED = (
    "POINT_R73_L",
    "POINT_R73_R",
    "POINT_LAUNCHER_AIM",
    "CENTER_LAUNCHER",
    "Launcher_Azimuth_Pivot",
    "Launcher_Elevation_Pivot",
    "EOIR_Azimuth_Pivot",
    "EOIR_Elevation_Pivot",
)
SAMPLE_FRAMES = (50, 100, 150)

MAX_SMALL_DIM = 0.35
DETACHED_GAP = 0.07
MIN_Z = 0.45
STRICT_ATTACHMENT_GAP = 0.0015

NAME_PROTECT_TOKENS = (
    "POINT_", "CENTER_", "COLLISION", "Collision", "BOUND", "Bounding",
    "Hull", "HULL", "Deck", "DECK", "Fender", "Rubrail", "Rail", "RAIL",
    "Launcher", "EOIR", "Sensor", "Optic", "Lens", "Missile", "R73", "AIM9",
    "Mast", "Pedestal", "Waterjet", "ENGINE", "Damage", "DM_",
)


def snapshot():
    snap = {}
    for frame in SAMPLE_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name in PROTECTED:
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise RuntimeError(f"Protected object missing: {name}")
            snap[(frame, name)] = obj.matrix_world.copy()
    bpy.context.scene.frame_set(100)
    bpy.context.view_layer.update()
    return snap


def matrix_delta(a, b):
    return max(abs(a[r][c] - b[r][c]) for r in range(4) for c in range(4))


def aabb(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    dims = mx - mn
    center = (mn + mx) * 0.5
    return mn, mx, dims, center


def aabb_gap(a0, a1, b0, b1):
    dx = max(0.0, b0.x - a1.x, a0.x - b1.x)
    dy = max(0.0, b0.y - a1.y, a0.y - b1.y)
    dz = max(0.0, b0.z - a1.z, a0.z - b1.z)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def object_gap(a, b):
    a0, a1, _, _ = aabb(a)
    b0, b1, _, _ = aabb(b)
    return aabb_gap(a0, a1, b0, b1)


def in_lod0(obj):
    return any(c.name == LOD0 for c in obj.users_collection)


def name_protected(name):
    if name in PROTECTED:
        return True
    return any(tok in name for tok in NAME_PROTECT_TOKENS)


def move_world(obj, delta):
    """Translate a visual mesh in world space while retaining its parent/hierarchy."""
    bpy.context.view_layer.update()
    m = obj.matrix_world.copy()
    m.translation = m.translation + Vector(delta)
    obj.matrix_world = m
    bpy.context.view_layer.update()


def snap_known_hovering_details():
    # The DCS screenshots exposed three specific construction errors which a
    # coarse 7 cm detached-object detector cannot catch: black 'web-hole' discs
    # 5 mm off the missile rail, pivot-bolt discs 2 mm off the rail, and cable
    # glands / fairing fasteners hovering 8-12.5 mm above their panels. Embed
    # each slightly into its intended support so no daylight can appear.
    moved = []
    checks = []

    def shift_prefix(prefix, delta, support_name):
        support = bpy.data.objects.get(support_name)
        if support is None:
            raise RuntimeError(f"V5 support missing: {support_name}")
        for obj in sorted((o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(prefix)), key=lambda o: o.name):
            before_gap = object_gap(obj, support)
            move_world(obj, delta)
            after_gap = object_gap(obj, support)
            rec = {
                "name": obj.name,
                "support": support_name,
                "delta_world": [float(v) for v in delta],
                "gap_before": round(float(before_gap), 6),
                "gap_after": round(float(after_gap), 6),
            }
            moved.append(rec)
            checks.append(rec)

    # Rail side decorative discs: move inward past the actual rail skin.
    shift_prefix("APU73_WebHole_L_", (0.0, -0.0065, 0.0), "APU73_Rail_L")
    shift_prefix("APU73_WebHole_R_", (0.0, +0.0065, 0.0), "APU73_Rail_R")
    shift_prefix("Rail_PivotBolt_L_", (0.0, -0.0035, 0.0), "APU73_Rail_L")
    shift_prefix("Rail_PivotBolt_R_", (0.0, +0.0035, 0.0), "APU73_Rail_R")

    # Two forward cable glands visibly floated above the launcher fairing.
    for name, support_name in (
        ("Cable_Gland_0", "Launcher_Fairing_Port"),
        ("Cable_Gland_1", "Launcher_Fairing_Starboard"),
    ):
        obj = bpy.data.objects.get(name)
        support = bpy.data.objects.get(support_name)
        if obj is None or support is None:
            raise RuntimeError(f"V5 attachment/support missing: {name} / {support_name}")
        before_gap = object_gap(obj, support)
        move_world(obj, (0.0, 0.0, -0.0155))
        after_gap = object_gap(obj, support)
        rec = {
            "name": name, "support": support_name,
            "delta_world": [0.0, 0.0, -0.0155],
            "gap_before": round(float(before_gap), 6),
            "gap_after": round(float(after_gap), 6),
        }
        moved.append(rec); checks.append(rec)

    # Fairing side fasteners 1-4 were modeled 8 mm outside the panel skin.
    for side, sign, support_name in (
        ("Port", -1.0, "Launcher_Fairing_Port"),
        ("Starboard", +1.0, "Launcher_Fairing_Starboard"),
    ):
        support = bpy.data.objects.get(support_name)
        if support is None:
            raise RuntimeError(f"V5 support missing: {support_name}")
        for i in range(1, 5):
            name = f"Fairing_Fastener_{side}_{i}"
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            before_gap = object_gap(obj, support)
            delta = (0.0, sign * 0.0100, 0.0)
            move_world(obj, delta)
            after_gap = object_gap(obj, support)
            rec = {
                "name": name, "support": support_name,
                "delta_world": [float(v) for v in delta],
                "gap_before": round(float(before_gap), 6),
                "gap_after": round(float(after_gap), 6),
            }
            moved.append(rec); checks.append(rec)

    bad = [r for r in checks if r["gap_after"] > STRICT_ATTACHMENT_GAP]
    if bad:
        raise RuntimeError(f"V5 flush-attachment QA failed: {bad}")
    return moved, bad


before = snapshot()
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()

# First fix the near-surface objects that looked detached despite being less than
# 7 cm from their intended supports.
snapped_attachments, bad_attachment_gaps = snap_known_hovering_details()

# Then remove truly detached small visual meshes.
meshes = [o for o in bpy.data.objects if o.type == "MESH" and in_lod0(o)]
boxes = {o.name: aabb(o) for o in meshes}
structural = []
for obj in meshes:
    mn, mx, dims, center = boxes[obj.name]
    if max(dims) > MAX_SMALL_DIM or name_protected(obj.name):
        structural.append(obj)

candidates = []
for obj in meshes:
    if name_protected(obj.name):
        continue
    mn, mx, dims, center = boxes[obj.name]
    if max(dims) > MAX_SMALL_DIM or mn.z < MIN_Z:
        continue
    nearest_name = None
    nearest_gap = float("inf")
    for support in structural:
        if support == obj:
            continue
        smn, smx, _, _ = boxes[support.name]
        gap = aabb_gap(mn, mx, smn, smx)
        if gap < nearest_gap:
            nearest_gap = gap
            nearest_name = support.name
    candidates.append({
        "name": obj.name,
        "dims": [round(float(v), 5) for v in dims],
        "center": [round(float(v), 5) for v in center],
        "min_z": round(float(mn.z), 5),
        "nearest_structural": nearest_name,
        "nearest_gap": round(float(nearest_gap), 5),
        "remove": bool(nearest_gap > DETACHED_GAP),
    })

removed = []
for item in candidates:
    if not item["remove"]:
        continue
    obj = bpy.data.objects.get(item["name"])
    if obj is not None:
        removed.append(item)
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.context.view_layer.update()

remaining_detached = []
meshes2 = [o for o in bpy.data.objects if o.type == "MESH" and in_lod0(o)]
boxes2 = {o.name: aabb(o) for o in meshes2}
structural2 = []
for obj in meshes2:
    mn, mx, dims, center = boxes2[obj.name]
    if max(dims) > MAX_SMALL_DIM or name_protected(obj.name):
        structural2.append(obj)
for obj in meshes2:
    if name_protected(obj.name):
        continue
    mn, mx, dims, center = boxes2[obj.name]
    if max(dims) > MAX_SMALL_DIM or mn.z < MIN_Z:
        continue
    nearest_gap = float("inf")
    nearest_name = None
    for support in structural2:
        if support == obj:
            continue
        smn, smx, _, _ = boxes2[support.name]
        gap = aabb_gap(mn, mx, smn, smx)
        if gap < nearest_gap:
            nearest_gap = gap
            nearest_name = support.name
    if nearest_gap > DETACHED_GAP:
        remaining_detached.append({
            "name": obj.name,
            "center": [round(float(v), 5) for v in center],
            "dims": [round(float(v), 5) for v in dims],
            "nearest_structural": nearest_name,
            "nearest_gap": round(float(nearest_gap), 5),
        })

# Functional freeze.
after = snapshot()
max_delta = 0.0
for key, m0 in before.items():
    d = matrix_delta(m0, after[key])
    max_delta = max(max_delta, d)
    if d > 1.0e-6:
        raise RuntimeError(f"FUNCTIONAL TRANSFORM CHANGED {key}: {d}")

report = {}
if REPORT.exists():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
report["refinement_v5"] = {
    "status": "success" if not remaining_detached and not bad_attachment_gaps else "needs_review",
    "purpose": "remove detached small meshes and force near-surface rail/fairing details flush to supports",
    "max_small_dim_m": MAX_SMALL_DIM,
    "detached_gap_m": DETACHED_GAP,
    "strict_attachment_gap_m": STRICT_ATTACHMENT_GAP,
    "snapped_visual_attachments": snapped_attachments,
    "bad_attachment_gaps": bad_attachment_gaps,
    "candidate_count": len(candidates),
    "removed_detached_objects": removed,
    "remaining_detached_candidates": remaining_detached,
    "functional_transform_max_delta": max_delta,
    "policy": "visual-only mesh placement/removal; protected turret/sensor/connectors unchanged",
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("MAGURA_HIRES_REFINEMENT_V5_READY=1")
print(json.dumps(report["refinement_v5"], indent=2))
