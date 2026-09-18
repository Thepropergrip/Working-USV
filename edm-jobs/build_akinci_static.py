from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial

UID = "6888b15081a8436f83baf35f5e0d50ed"
SOURCE_URL = "https://sketchfab.com/3d-models/bayraktar-akinci-6888b15081a8436f83baf35f5e0d50ed"
AUTHOR = "Kellot"
LICENSE = "CC BY 4.0"

TARGET_LENGTH_M = 12.3
TARGET_SPAN_M = 20.0
TARGET_HEIGHT_M = 4.1

WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
ARTIFACT_DIR = WORKSPACE / "edm-artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
CLI_DIR = WORKSPACE / "_sketchfab_cli"
DOWNLOAD_DIR = WORKSPACE / "_akinci_download"


def run(cmd, cwd=None):
    print("[AKINCI RUN]", " ".join(str(x) for x in cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def acquire_source() -> Path:
    if CLI_DIR.exists():
        shutil.rmtree(CLI_DIR)
    if DOWNLOAD_DIR.exists():
        shutil.rmtree(DOWNLOAD_DIR)

    run(["git", "clone", "--depth", "1", "https://github.com/seryi882/sketchfab-cli.git", str(CLI_DIR)])
    py = shutil.which("python") or shutil.which("python3")
    if not py:
        raise RuntimeError("Python executable not found on runner.")

    run([py, "-m", "pip", "install", "-q", "-r", str(CLI_DIR / "requirements.txt")])
    run([py, str(CLI_DIR / "main.py"), "-q", "-o", str(DOWNLOAD_DIR), UID], cwd=str(CLI_DIR))

    gltfs = list(DOWNLOAD_DIR.rglob("*.gltf"))
    if len(gltfs) != 1:
        raise RuntimeError(f"Expected exactly one glTF, found {gltfs}")
    print("[AKINCI] Source glTF:", gltfs[0], flush=True)
    return gltfs[0]


def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def meshes():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def roots(objects):
    s = set(objects)
    return [o for o in objects if o.parent not in s]


def world_bounds(objects):
    pts = []
    for o in objects:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    if not pts:
        raise RuntimeError("No mesh bounds available.")
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo, hi


def obj_bounds(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo, hi


def apply_to_roots(objects, matrix):
    for o in roots(objects):
        o.matrix_world = matrix @ o.matrix_world
    bpy.context.view_layer.update()


def remove_weapon_assembly():
    removed = []
    # The original source hierarchy names the store parent "bignomb.003_10".
    # Its two mesh children are the modeled weapon bodies/fittings.  The six
    # empty pylons are a separate object: _gltfNode_22 under Cube.007_9.
    for name in ("_gltfNode_24", "_gltfNode_25"):
        o = bpy.data.objects.get(name)
        if o is None:
            raise RuntimeError(f"Expected weapon mesh {name} was not found.")
        removed.append({
            "name": name,
            "vertices": len(o.data.vertices),
            "faces": len(o.data.polygons),
        })
        bpy.data.objects.remove(o, do_unlink=True)

    weapon_parent = bpy.data.objects.get("bignomb.003_10")
    if weapon_parent is not None:
        bpy.data.objects.remove(weapon_parent, do_unlink=True)

    pylon = bpy.data.objects.get("_gltfNode_22")
    if pylon is None or pylon.type != "MESH":
        raise RuntimeError("Empty pylon mesh _gltfNode_22 was not found.")
    pylon.name = "AKINCI_EMPTY_PYLONS_6_STATION"
    pylon.data.name = "AKINCI_EMPTY_PYLONS_6_STATION_MESH"
    if len(pylon.data.vertices) != 144:
        raise RuntimeError(f"Unexpected pylon geometry: {len(pylon.data.vertices)} verts.")
    print("[AKINCI] Removed weapon assembly; retained six-station empty pylons.", flush=True)
    return removed, pylon


def orient_scale_place():
    visual = meshes()
    lo, hi = world_bounds(visual)
    ext = hi - lo
    if min(ext) <= 0:
        raise RuntimeError(f"Invalid source bounds: {lo} {hi}")

    # Imported source convention: X = span, Y = longitudinal (tail is +Y),
    # Z = vertical. DCS asset convention used by our established EDM builds:
    # +X = forward, Y = lateral, +Z = up.
    #
    # Scale each envelope axis to Baykar's published AKINCI dimensions, then
    # rotate so the nose points +X.
    scale_span = TARGET_SPAN_M / ext.x
    scale_length = TARGET_LENGTH_M / ext.y
    scale_height = TARGET_HEIGHT_M / ext.z

    transform = Matrix((
        (0.0, -scale_length, 0.0, 0.0),
        (scale_span, 0.0, 0.0, 0.0),
        (0.0, 0.0, scale_height, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    apply_to_roots(list(bpy.context.scene.objects), transform)

    visual = meshes()
    lo, hi = world_bounds(visual)
    # Center footprint on the origin and put lowest landing-gear contact at Z=0.
    t = Matrix.Translation((
        -(lo.x + hi.x) * 0.5,
        -(lo.y + hi.y) * 0.5,
        -lo.z,
    ))
    apply_to_roots(list(bpy.context.scene.objects), t)

    lo2, hi2 = world_bounds(meshes())
    ext2 = hi2 - lo2
    target = Vector((TARGET_LENGTH_M, TARGET_SPAN_M, TARGET_HEIGHT_M))
    if max(abs(ext2[i] - target[i]) for i in range(3)) > 0.005:
        raise RuntimeError(f"Final dimensions mismatch: got {tuple(ext2)}, expected {tuple(target)}")

    print("[AKINCI] Final bounds:", tuple(round(v, 4) for v in lo2), tuple(round(v, 4) for v in hi2), flush=True)
    print("[AKINCI] Final dimensions:", tuple(round(v, 4) for v in ext2), flush=True)
    return lo2, hi2, ext2


def material_color(old):
    # Preserve the simple color-only source materials as closely as possible.
    if old is None:
        return (0.22, 0.23, 0.22, 1.0)
    try:
        if old.use_nodes and old.node_tree:
            bsdf = next((n for n in old.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf and bsdf.inputs.get("Base Color"):
                c = bsdf.inputs["Base Color"].default_value
                return (float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    except Exception:
        pass
    try:
        c = old.diffuse_color
        return (float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    except Exception:
        return (0.5, 0.5, 0.5, 1.0)


def create_edm_material(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = color
    m.node_tree.nodes.clear()

    descs = build_material_descriptions()
    desc = descs.get(DefaultMaterial.name)
    if desc is None:
        raise RuntimeError("ED Default Material description unavailable.")

    group = m.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
    group.post_init(desc)
    group.name = "EDM_Default"

    base = group.inputs.get("Base Color")
    if base is None:
        raise RuntimeError("ED material has no Base Color socket.")
    base.default_value = color

    alpha = group.inputs.get("Base Alpha*")
    if alpha is not None:
        alpha.default_value = float(color[3])

    return m


def convert_materials():
    originals = {}
    for o in meshes():
        for slot in o.material_slots:
            old = slot.material
            key = old.name if old else "__NO_MATERIAL__"
            if key not in originals:
                originals[key] = material_color(old)

    edm = {}
    for key, color in originals.items():
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in key)
        edm[key] = create_edm_material("AKINCI_" + safe, color)

    fallback = create_edm_material("AKINCI_PYLON_DARK_METAL", (0.18, 0.19, 0.18, 1.0))

    for o in meshes():
        # Pylons arrive with no material assignment in the public/source scene.
        if len(o.material_slots) == 0:
            o.data.materials.append(fallback)
        else:
            for slot in o.material_slots:
                old = slot.material
                key = old.name if old else "__NO_MATERIAL__"
                slot.material = edm[key]
        try:
            o.EDMProps.TWO_SIDED = True
        except Exception:
            pass

    print(f"[AKINCI] Converted {len(edm) + 1} materials to native ED Default Material.", flush=True)


def collision_box(name, lo, hi, shrink=(1.0, 1.0, 1.0)):
    center = (lo + hi) * 0.5
    dims = hi - lo
    dims = Vector((dims.x * shrink[0], dims.y * shrink[1], dims.z * shrink[2]))
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.clear()
    o.EDMProps.SPECIAL_TYPE = "COLLISION_SHELL"
    o.display_type = "WIRE"
    o.hide_render = True
    return o


def add_collision_shells():
    # Use the source's primary fuselage/wing/tail objects so collision follows
    # the actual aircraft instead of one giant full-envelope box.
    # Names survive glTF import until the collision shell is created.
    source_map = {
        "fuselage": "_gltfNode_0",
        "main_wing": "_gltfNode_4",
        "tailplane": "_gltfNode_2",
    }
    created = []
    for role, obj_name in source_map.items():
        o = bpy.data.objects.get(obj_name)
        if o is None:
            raise RuntimeError(f"Collision source {obj_name} missing.")
        lo, hi = obj_bounds(o)
        shrink = (0.92, 0.90, 0.82) if role == "fuselage" else (0.92, 0.98, 0.55)
        created.append(collision_box(f"COLLISION_SHELL_AKINCI_{role.upper()}", lo, hi, shrink))
    print("[AKINCI] Collision shells:", [o.name for o in created], flush=True)
    return created


def rename_visuals():
    names = {
        "_gltfNode_0": "AKINCI_FUSELAGE_PRIMARY",
        "_gltfNode_2": "AKINCI_TAILPLANE",
        "_gltfNode_4": "AKINCI_MAIN_WING",
    }
    for old, new in names.items():
        o = bpy.data.objects.get(old)
        if o:
            o.name = new


def main():
    gltf = acquire_source()
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(gltf))
    bpy.context.view_layer.update()

    imported_meshes = meshes()
    if len(imported_meshes) != 18:
        raise RuntimeError(f"Expected 18 source meshes, found {len(imported_meshes)}")

    removed, pylon = remove_weapon_assembly()
    lo, hi, dims = orient_scale_place()
    convert_materials()
    collisions = add_collision_shells()
    rename_visuals()

    pylon_after = bpy.data.objects.get("AKINCI_EMPTY_PYLONS_6_STATION")
    if pylon_after is None:
        raise RuntimeError("Pylons disappeared during build.")
    if bpy.data.objects.get("_gltfNode_24") or bpy.data.objects.get("_gltfNode_25"):
        raise RuntimeError("Weapon mesh still exists after removal.")

    manifest = {
        "status": "ready_for_edm_export",
        "asset": "TPG Bayraktar AKINCI Static",
        "source_uid": UID,
        "source_url": SOURCE_URL,
        "source_author": AUTHOR,
        "source_license": LICENSE,
        "published_dimensions_m": {
            "length": TARGET_LENGTH_M,
            "wingspan": TARGET_SPAN_M,
            "height": TARGET_HEIGHT_M,
        },
        "final_bounds_min": [float(v) for v in lo],
        "final_bounds_max": [float(v) for v in hi],
        "final_dimensions": [float(v) for v in dims],
        "weapons_removed": removed,
        "empty_pylons_retained": {
            "object": pylon_after.name,
            "vertices": len(pylon_after.data.vertices),
            "faces": len(pylon_after.data.polygons),
        },
        "visual_mesh_count": len([o for o in meshes() if not o.name.startswith("COLLISION_SHELL")]),
        "collision_shell_count": len(collisions),
    }
    (ARTIFACT_DIR / "akinci-build-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print("[AKINCI] BUILD_READY_FOR_NATIVE_EDM_EXPORT")
    print(json.dumps(manifest, indent=2))


main()
