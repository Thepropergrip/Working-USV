"""Grizzly visual repair; the approved missile/lid rig is read-only."""
import bpy, hashlib, json, os, subprocess, zipfile
from pathlib import Path
from mathutils import Vector

out = Path(os.environ['GITHUB_WORKSPACE']) / 'edm-artifacts'
out.mkdir(parents=True, exist_ok=True)

def freeze():
    actions = {}
    for a in bpy.data.actions:
        actions[a.name] = [(f.data_path, f.array_index, [(list(k.co), k.interpolation, list(k.handle_left), list(k.handle_right)) for k in f.keyframe_points]) for f in a.fcurves]
    transforms = {}
    for o in bpy.data.objects:
        transforms[o.name] = {'parent': o.parent.name if o.parent else None, 'local': [list(r) for r in o.matrix_basis], 'inverse': [list(r) for r in o.matrix_parent_inverse]}
    poses = {}
    for frame in (100, 120, 140, 165, 180, 200):
        bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
        poses[str(frame)] = {o.name: [list(r) for r in o.matrix_world] for o in bpy.data.objects if o.name.startswith(('POINT_GRZ4535','GRZ4535_', 'Roof_','RoofActuator_'))}
    bpy.context.scene.frame_set(100); bpy.context.view_layer.update()
    return {'actions': actions, 'transforms': transforms, 'poses': poses}

def bounds(o):
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    return [[min(v[i] for v in pts), max(v[i] for v in pts)] for i in range(3)]

def audit():
    return [{'name': o.name, 'parent': o.parent.name if o.parent else None, 'type': o.type, 'location': list(o.location), 'bounds': bounds(o) if o.type == 'MESH' else None, 'collections': [c.name for c in o.users_collection]} for o in bpy.data.objects]

locked = freeze()
before = audit()
changes = []

def world_axis(o, axis, lo, hi):
    # The earlier build mistakenly placed world-space target bounds into
    # local vertex coordinates. The object's translation was then added twice.
    world = [o.matrix_world @ v.co for v in o.data.vertices]
    old_lo = min(p[axis] for p in world); old_hi = max(p[axis] for p in world)
    inv = o.matrix_world.inverted()
    for vertex, point in zip(o.data.vertices, world):
        point[axis] = lo + (point[axis] - old_lo) * (hi - lo) / (old_hi - old_lo)
        vertex.co = inv @ point
    o.data.update()

for suffix, lo, hi in (('R', -1.13256, -.06244), ('L', .06244, 1.13256)):
    for prefix, yl, yh, zl, zh in (
        ('DoorInnerPanel_', lo, hi, .345, 2.555),
        ('DoorGasket_', -1.180 if suffix == 'R' else .015, -.015 if suffix == 'R' else 1.180, .300, 2.600),
    ):
        o = bpy.data.objects[prefix + suffix]
        old = bounds(o)
        world_axis(o, 1, yl, yh); world_axis(o, 2, zl, zh)
        changes.append({'object': o.name, 'before': old, 'after': bounds(o)})
for name, zl, zh in [('DoorCenterSeal', .310, 2.590), ('RearInner', .375, 2.535), ('RearWeld_-1.08', .375, 2.535), ('RearWeld_1.08', .375, 2.535)]:
    o = bpy.data.objects[name]; old = bounds(o)
    world_axis(o, 2, zl, zh)
    changes.append({'object': name, 'before': old, 'after': bounds(o)})
for level in (1, 2, 3):
    o = bpy.data.objects.get('LOD%d_Doors' % level)
    if o:
        world_axis(o, 1, -1.18, 1.18); world_axis(o, 2, .30, 2.60)
    o = bpy.data.objects.get('LOD%d_Rear' % level)
    if o: world_axis(o, 2, .375, 2.535)

# Atlas layout in image coordinates: top row = front, side P, side S;
# bottom row = rear, roof, plain paint. Blender UV V increases upward.
def set_uv(o, tile, coord):
    if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')
    uv = o.data.uv_layers.active.data
    col, row = tile % 3, tile // 3
    pad = .002
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            p = o.matrix_world @ o.data.vertices[o.data.loops[li].vertex_index].co
            s, t = coord(p)
            s = max(0., min(1., s)); t = max(0., min(1., t))
            uv[li].uv = ((col + pad + s * (1 - 2*pad)) / 3, 1 - (row + pad + t * (1 - 2*pad)) / 2)

uv_fixed = []
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    n = o.name
    if n.startswith('PressedDoor_') or (n.startswith('LOD') and n.endswith('_Doors')):
        set_uv(o, 0, lambda p: ((p.y + 1.18) / 2.36, (2.60 - p.z) / 2.30)); uv_fixed.append(n)
    elif n == 'PressedRear' or (n.startswith('LOD') and n.endswith('_Rear')):
        set_uv(o, 3, lambda p: ((1.081 - p.y) / 2.162, (2.535 - p.z) / 2.16)); uv_fixed.append(n)
    elif n.startswith('PressedSide_') or (n.startswith('LOD') and '_Side_' in n):
        positive = sum(v.co.y for v in o.data.vertices) / len(o.data.vertices) + o.location.y > 0
        if positive: set_uv(o, 1, lambda p: ((1.35 - p.x) / 2.70, (2.46 - p.z) / 1.96))
        else: set_uv(o, 2, lambda p: ((p.x + 1.35) / 2.70, (2.46 - p.z) / 1.96))
        uv_fixed.append(n)
    elif n in ('Roof_Port', 'Roof_Starboard', 'Roof_Aft') or (n.startswith('LOD') and n.endswith(('_RoofPort', '_RoofStbd'))):
        set_uv(o, 4, lambda p: ((p.x + 1.43) / 2.86, (1.31 - p.y) / 2.62)); uv_fixed.append(n)

# White albedo multipliers prevent the former procedural brown paint factor
# from tinting the supplied gray texture. Surface maps remain the supplied maps.
for m in bpy.data.materials:
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.bl_idname == 'EdmDefaultShaderNodeType' and 'Base Color' in n.inputs:
                n.inputs['Base Color'].default_value = (1., 1., 1., 1.)

# Preserve every animation curve, parent, transform, and sampled connector pose.
check = freeze()
if check != locked: raise RuntimeError('Visual repair modified locked rig data')
for item in changes:
    if item['after'][2][1] > 2.61: raise RuntimeError('Static infill still extends above roof: ' + item['object'])
(out / 'grizzly_object_audit_before.json').write_text(json.dumps(before, indent=2))
(out / 'grizzly_object_audit_after.json').write_text(json.dumps(audit(), indent=2))
(out / 'grizzly_visual_repair_validation.json').write_text(json.dumps({'static_world_space_repairs': changes, 'uv_fixed': uv_fixed, 'locked_rig_equal': True, 'locked_rig_sha256': hashlib.sha256(json.dumps(locked, sort_keys=True).encode()).hexdigest()}, indent=2))
(out / 'grizzly_locked_rig.json').write_text(json.dumps(locked, indent=2))
print('GRIZZLY_STATIC_REPAIR_PASS', len(changes), 'RIG_UNCHANGED', flush=True)

# Optional validation tools/reference acquisition. A failed tool download must
# never suppress the repaired EDM or validation report.
def acquire(url, name):
    target = out / name
    command = "$ErrorActionPreference='Stop'; Invoke-WebRequest -UserAgent 'Mozilla/5.0' -Uri '" + url.replace("'", "''") + "' -OutFile '" + str(target).replace("'", "''") + "' -TimeoutSec 90"
    try:
        subprocess.run(['pwsh', '-NoProfile', '-Command', command], check=True, timeout=100)
        print('ACQUIRED', name, target.stat().st_size, flush=True)
        return True
    except Exception as exc:
        print('OPTIONAL_ACQUIRE_FAILED', name, str(exc), flush=True)
        if target.exists(): target.unlink()
        return False

if not acquire('https://download.blender.org/release/Blender4.1/blender-4.1.1-linux-x64.tar.xz', 'blender-4.1.1-linux-x64.tar.xz'):
    acquire('https://mirrors.ocf.berkeley.edu/blender/release/Blender4.1/blender-4.1.1-linux-x64.tar.xz', 'blender-4.1.1-linux-x64.tar.xz')
acquire('https://upload.wikimedia.org/wikipedia/commons/c/c7/%22M81%22_U.S._woodland_camouflage_pattern_swatch.png', 'm81_reference.png')
acquire('https://codeload.github.com/devozdemirhasancan/DCS-EDM-Blender-Importer/zip/refs/heads/main', 'edm_importer_source.zip')
addon = Path(os.environ['BLENDER_USER_SCRIPTS']) / 'addons' / 'io_scene_edm'
with zipfile.ZipFile(out / 'official_exporter_python_reference.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for p in addon.rglob('*.py'): z.write(p, p.relative_to(addon))
bpy.context.scene.frame_set(100); bpy.context.view_layer.update()
