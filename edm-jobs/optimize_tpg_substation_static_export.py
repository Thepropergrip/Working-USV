import bpy
from collections import defaultdict

# Export-only optimization for the heavy LOD0 static models.
# Merge only plain, parentless visual mesh objects that have no modifiers,
# constraints, animation, or custom properties. This preserves transforms,
# materials and visible geometry while drastically reducing EDM node count.
# EDM-special objects/connectors/collision/custom-property nodes are untouched.

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
    if len(objs) < 2:
        continue
    # Keep batches bounded to avoid one pathological mega-join while still
    # cutting node count by orders of magnitude.
    for start in range(0, len(objs), 250):
        batch = [o for o in objs[start:start+250] if o.name in bpy.context.scene.objects]
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
print(f'[TPG export optimization] mesh objects {before} -> {after}; merged {joined_objects} objects in {joined_groups} batches')
