import bpy

INTACT = ("MAGURA_LOD_0_90", "MAGURA_LOD_1_250", "MAGURA_LOD_2_800", "MAGURA_LOD_3_2500")
DESTROYED = ("DESTROYED_LOD_0_100", "DESTROYED_LOD_1_400", "DESTROYED_LOD_2_1800")
SUPPORT = ("COLLISION", "BOUNDING_BOX", "CONNECTORS")


def visible(name, state):
    col = bpy.data.collections.get(name)
    if col is None:
        return
    col.hide_viewport = not state
    col.hide_render = not state


for name in INTACT:
    visible(name, False)
for name in DESTROYED:
    visible(name, True)
for name in SUPPORT:
    visible(name, True)

# HiRes visual additions are in intact LOD collections and therefore remain out
# of the destroyed export. Material/image upgrades are shared and remain active.
bpy.context.scene.frame_set(100)
bpy.context.view_layer.update()
print("MAGURA_HIRES_DESTROYED_VISIBILITY_READY=1")
