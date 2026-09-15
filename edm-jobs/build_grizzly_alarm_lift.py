import math, os, runpy, sys, tarfile, tempfile
from pathlib import Path
import bpy
from mathutils import Vector

workspace = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
archive = workspace / 'edm-jobs' / 'grizzly_rc4_scripts.tgz'
root = Path(tempfile.mkdtemp(prefix='grizzly_alarm_lift_'))
with tarfile.open(archive, mode='r:gz') as tf:
    tf.extractall(root)

# Blender 4.1 headless compatibility: UV assignment must happen in Object Mode.
model_path = root / '02_model.py'
model = model_path.read_text(encoding='utf-8')
old_uv = '''    bpy.ops.object.modifier_apply(modifier=solid.name); bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    grizzly_release_uv(obj)
    bpy.ops.object.mode_set(mode="OBJECT")
'''
new_uv = '''    bpy.ops.object.modifier_apply(modifier=solid.name); bpy.ops.object.modifier_apply(modifier=bevel.name)
    grizzly_release_uv(obj)
'''
if old_uv not in model:
    raise RuntimeError('Expected GRIZZLY UV block not found')
model_path.write_text(model.replace(old_uv, new_uv), encoding='utf-8')

sys.path.insert(0, str(root))
runpy.run_path(str(root / '01_scene_setup.py'), run_name='__main__')
runpy.run_path(str(root / '02_model.py'), run_name='__main__')

from grizzly_common import (
    DESTROYED_LODS, INTACT_LODS, SUPPORT_COLLECTIONS,
    add_connector, animate_rotation, animate_rotation_keys,
    collection, parent_keep_world, set_collection_visible,
)

# ---------- R3 panel-fit geometry ----------
def remap_mesh_axis_bounds(obj, axis, new_lo, new_hi):
    vals = [v.co[axis] for v in obj.data.vertices]
    old_lo, old_hi = min(vals), max(vals)
    if abs(old_hi-old_lo) < 1e-9:
        return
    scale = (new_hi-new_lo)/(old_hi-old_lo)
    for v in obj.data.vertices:
        v.co[axis] = new_lo + (v.co[axis]-old_lo)*scale
    obj.data.update()

# Front corrugated leaves: close the center/top/bottom gaps to the accepted R3 fit.
for suffix, ylo, yhi in (('R', -1.151, -0.048), ('L', 0.048, 1.151)):
    face = bpy.data.objects.get('PressedDoor_'+suffix)
    if face:
        remap_mesh_axis_bounds(face, 1, ylo, yhi)
        remap_mesh_axis_bounds(face, 2, 0.335, 2.565)
    inner = bpy.data.objects.get('DoorInnerPanel_'+suffix)
    if inner:
        remap_mesh_axis_bounds(inner, 1, -1.13256 if suffix=='R' else 0.06244, -0.06244 if suffix=='R' else 1.13256)
        remap_mesh_axis_bounds(inner, 2, 0.345, 2.555)
    gasket = bpy.data.objects.get('DoorGasket_'+suffix)
    if gasket:
        remap_mesh_axis_bounds(gasket, 1, -1.180 if suffix=='R' else 0.015, -0.015 if suffix=='R' else 1.180)
        remap_mesh_axis_bounds(gasket, 2, 0.300, 2.600)

seal = bpy.data.objects.get('DoorCenterSeal')
if seal:
    remap_mesh_axis_bounds(seal, 2, 0.310, 2.590)

# Shift door-side hardware outward/slightly taller so it follows the enlarged leaves.
for obj in bpy.data.objects:
    n = obj.name
    if n.startswith(('LockRod_','LockCam_','CamKeeper_','LockHandle_','HandleRetainer_')):
        obj.location.y *= 1.045
        obj.location.z = 0.30 + (obj.location.z-0.43) * ((2.60-0.30)/(2.53-0.43))
    elif n.startswith(('DoorHingePin_','DoorHingeLeaf_')):
        obj.location.y *= 1.035
        obj.location.z = 0.30 + (obj.location.z-0.43) * ((2.60-0.30)/(2.53-0.43))

# Rear panel fit retained from R3.
rear = bpy.data.objects.get('PressedRear')
if rear: remap_mesh_axis_bounds(rear, 2, 0.375, 2.535)
rear_inner = bpy.data.objects.get('RearInner')
if rear_inner: remap_mesh_axis_bounds(rear_inner, 2, 0.375, 2.535)
for obj in bpy.data.objects:
    if obj.name.startswith('RearWeld_') and obj.type == 'MESH':
        remap_mesh_axis_bounds(obj, 2, 0.375, 2.535)
for name,z in (('RearRail_0.43',0.315),('RearRail_2.53',2.595)):
    obj=bpy.data.objects.get(name)
    if obj: obj.location.z=z

# ---------- lid sequence + clipping fix ----------
# Alarm argument 40: green=0 (frame 100), red=+1 (frame 200).
# Lids finish opening at 65% of transition; missiles remain stowed until then.
roof_specs = {
    'Roof_Port_Pivot': (0, 86.0),
    'Roof_Starboard_Pivot': (0, -86.0),
    'Roof_Aft_Pivot': (1, 76.0),
}
for pivot_name,(axis,high) in roof_specs.items():
    pivot=bpy.data.objects.get(pivot_name)
    if pivot is None:
        raise RuntimeError(f'Missing {pivot_name}')
    animate_rotation_keys(pivot,40,axis,((0,0.0),(100,0.0),(165,high),(200,high)))

# Hinge/bolt cylinders were static while the lid rotated, producing intermittent clipping.
# Make them part of the moving lid and lift the middle head 15 mm clear of the gray panel.
for roof in ('Roof_Port','Roof_Starboard','Roof_Aft'):
    pivot=bpy.data.objects.get(roof+'_Pivot')
    if pivot is None: continue
    for obj in list(bpy.data.objects):
        if obj.name.startswith(roof+'_Hinge_'):
            if obj.name == roof+'_Hinge_0':
                obj.location.z += 0.015
            parent_keep_world(obj,pivot)

# ---------- native external-missile connector lift ----------
READY_Z = 2.84
STOW_Z = 1.74
DROP = READY_Z - STOW_Z
CELL_POSITIONS = ((-.66,-.37),(-.66,.37),(-.22,-.37),(-.22,.37),(.22,-.37),(.22,.37),(.66,-.37),(.66,.37))

lift=bpy.data.objects.new('GRZ4535_Missile_Lift_ARG40',None)
lift.empty_display_type='PLAIN_AXES'
lift.empty_display_size=0.10
collection('CONNECTORS').objects.link(lift)
action=bpy.data.actions.new('40_GRZ4535_Missile_Lift_ARG40')
lift.animation_data_create(); lift.animation_data.action=action
for frame,zoff in ((0,-DROP),(100,-DROP),(165,-DROP),(200,0.0)):
    lift.location=(0,0,zoff)
    lift.keyframe_insert('location',frame=frame,group='DCS Argument')
for curve in action.fcurves:
    for key in curve.keyframe_points:
        key.interpolation='LINEAR'

# Evaluate green/alarm-off pose before creating local child transforms.
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
for index,(x,y) in enumerate(CELL_POSITIONS,1):
    yaw=bpy.data.objects.new('GRZ4535_VLS_YAW_%02d'%index,None)
    yaw.empty_display_type='PLAIN_AXES'; yaw.empty_display_size=.09
    collection('CONNECTORS').objects.link(yaw)
    yaw.parent=lift
    yaw.location=(x,y,READY_Z)

    conn=add_connector('POINT_GRZ4535_%02d'%index,(0,0,0),rotation=(0,-math.pi/2,0))
    conn.parent=yaw
    conn.location=(0,0,0)
    animate_rotation(yaw,0,2,-180,180)

add_connector('CENTER_GRZ4535',(0,0,2.10))
add_connector('POINT_GRZ4535_SMOKE',(0,0,3.12))

# ---------- material names / texture references retained from R3 ----------
runpy.run_path(str(root / '03_materials.py'), run_name='__main__')
root_for_role={
    'body':'grzvu02_body','body_dark':'grzvu02_dark','steel':'grzvu02_paint',
    'metal':'grzvu02_metal','rail':'grzvu02_dark','hardware':'grzvu02_metal',
    'heatshield':'grzvu02_metal','connector':'grzvu02_metal','equipment':'grzvu02_dark',
    'antenna':'grzvu02_rubber','vent':'grzvu02_rubber','actuator':'grzvu02_metal',
    'label':'grzvu02_label','warning':'grzvu02_warning','stencil':'grzvu02_stencil',
    'weld':'grzvu02_paint','burnt':'grzvu02_burnt',
}
canonical={}
for role,rootname in root_for_role.items():
    mat=bpy.data.materials.get('GRIZZLY_'+role)
    if mat is None: continue
    mat.name='GRZVU02_'+role
    if not mat.use_nodes: continue
    for node in mat.node_tree.nodes:
        if node.type!='TEX_IMAGE' or node.image is None: continue
        old=node.image.name.lower()
        if 'roughmet' in old: kind='roughmet'
        elif 'normal' in old: kind='normal'
        else: kind='base'
        desired=f'{rootname}_{kind}'
        if desired in canonical:
            node.image=canonical[desired]
        else:
            node.image.name=desired
            canonical[desired]=node.image

# Export intact model only; destroyed shape stays the accepted R3 destroyed EDM in the package.
for name in INTACT_LODS + SUPPORT_COLLECTIONS:
    set_collection_visible(name,True)
for name in DESTROYED_LODS:
    set_collection_visible(name,False)

# Validate the alarm sequence.
def wz(obj):
    return float(obj.matrix_world.translation.z)
for frame,expected in ((100,STOW_Z),(165,STOW_Z),(200,READY_Z)):
    bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
    for i in range(1,9):
        c=bpy.data.objects.get('POINT_GRZ4535_%02d'%i)
        if c is None: raise RuntimeError(f'Missing connector {i}')
        if abs(wz(c)-expected)>0.02:
            raise RuntimeError(f'Connector {i} frame {frame} Z={wz(c):.3f}, expected {expected:.3f}')

bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print('GRIZZLY_USER_UPGRADE_VALIDATED stowedZ=%.2f readyZ=%.2f lidsDoneFrame=165'%(STOW_Z,READY_Z))
