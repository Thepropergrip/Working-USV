import bpy
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial

# DCS-ready static cube:
# - exact 1m dimensions
# - origin on ground plane (bottom Z = 0)
# - dark blue native ED material
# - dedicated EDM collision shell
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.5))
cube = bpy.context.object
cube.name = "TPG_1M_DARK_BLUE_CUBE_RENDER"
cube.dimensions = (1.0, 1.0, 1.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Current native Eagle Dynamics EDM material.
mat = bpy.data.materials.new("TPG_Dark_Blue_EDM")
mat.use_nodes = True
mat.diffuse_color = (0.02, 0.06, 0.20, 1.0)
mat.node_tree.nodes.clear()

material_descs = build_material_descriptions()
default_desc = material_descs.get(DefaultMaterial.name)
if default_desc is None:
    raise RuntimeError("ED Default Material description could not be loaded.")

edm_node = mat.node_tree.nodes.new(type=DefaultMaterial.node_group_name)
edm_node.post_init(default_desc)
edm_node.name = "EDM_Dark_Blue_Default"

base_color = edm_node.inputs.get("Base Color")
if base_color is None:
    raise RuntimeError("Native ED Default Material has no Base Color input.")
base_color.default_value = (0.02, 0.06, 0.20, 1.0)

base_alpha = edm_node.inputs.get("Base Alpha*")
if base_alpha is not None:
    base_alpha.default_value = 1.0

cube.data.materials.clear()
cube.data.materials.append(mat)

# Exact duplicate geometry used only as the native EDM collision shell.
collision = cube.copy()
collision.data = cube.data.copy()
collision.name = "TPG_1M_DARK_BLUE_CUBE_COLLISION"
bpy.context.collection.objects.link(collision)
collision.data.materials.clear()
collision.EDMProps.SPECIAL_TYPE = "COLLISION_SHELL"

# Metadata retained in the .blend source artifact.
cube["TPG_DCS_STATIC_TEST"] = True
cube["DIMENSION_METERS"] = 1.0
cube["COLOR_RGB"] = "0.02,0.06,0.20"
cube["EDM_SHADER_NODE_TYPE"] = edm_node.bl_idname
collision["TPG_COLLISION_SHELL"] = True

dims = tuple(round(v, 6) for v in cube.dimensions)
bbox_min_z = min((cube.matrix_world @ v.co).z for v in cube.data.vertices)
bbox_max_z = max((cube.matrix_world @ v.co).z for v in cube.data.vertices)

if dims != (1.0, 1.0, 1.0):
    raise RuntimeError(f"Cube dimensions are not exactly 1m: {dims}")
if abs(bbox_min_z) > 1e-6 or abs(bbox_max_z - 1.0) > 1e-6:
    raise RuntimeError(f"Ground placement geometry invalid: minZ={bbox_min_z}, maxZ={bbox_max_z}")
if collision.EDMProps.SPECIAL_TYPE != "COLLISION_SHELL":
    raise RuntimeError("Collision shell property was not applied.")

print(f"[TPG STATIC] Cube dimensions: {dims}")
print(f"[TPG STATIC] Ground extents: minZ={bbox_min_z:.6f}, maxZ={bbox_max_z:.6f}")
print(f"[TPG STATIC] Native EDM node: {edm_node.bl_idname}")
print(f"[TPG STATIC] Collision type: {collision.EDMProps.SPECIAL_TYPE}")
print(f"[TPG STATIC] Base Color: {tuple(base_color.default_value)}")
