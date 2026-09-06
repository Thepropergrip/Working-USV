import bpy
from collections import defaultdict

# Aggressive export-only optimization for the heavy substation models.
# Merge every safe plain visual mesh sharing the same material-slot signature
# into a single export mesh. This preserves geometry/material appearance while
# collapsing the EDM node count as far as possible. EDM-special objects,
# connectors, collision, animation/custom-property nodes remain untouched.

def is_plain_visual_mesh(obj):
    if obj.type != 'MESH':
        return False
    if obj.parent is not None:
        return False
    if obj.modifiers or obj.constraints or obj.animation_data is not None:
        return False
    if obj.keys():
        return False
    name = obj.name.upper()
    if any(tag in name for tag in ('COLLISION', 'CONNECTOR', 'BOUNDING', 'LIGHTNODE', 'LIGHT_NODE', 'USERBOX')):
        return False
    return True

buckets = defaultdict(list)
for obj in list(bpy.context.scene.objects):
    if not is_plain_visual_mesh(obj):
        continue
    mats = tuple((slot.material.name if slot.material else '') for slot in obj.material_slots)
    buckets[mats].append(obj)

before = sum(1 for o in bpy.context.scene.objects if o.type == 'MESH')
joined_groups = 0
joined_objects = 0

for mats, objs in buckets.items():
    batch = [o for o in objs if o.name in bpy.context.scene.objects]
    if len(batch) < 2:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in batch:
        o.select_set(True)
    bpy.context.view_layer.objects.active = batch[0]
    bpy.ops.object.join()
    batch[0].name = f'EXPORT_BATCH_{joined_groups:04d}'
    joined_groups += 1
    joined_objects += len(batch) - 1

bpy.ops.object.select_all(action='DESELECT')
after = sum(1 for o in bpy.context.scene.objects if o.type == 'MESH')
print(f'[TPG export optimization] mesh objects {before} -> {after}; merged {joined_objects} objects into {joined_groups} material batches')
