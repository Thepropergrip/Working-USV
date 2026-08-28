import bpy
from materials.materials import build_material_descriptions
from materials.material_default import DefaultMaterial

# Exact test geometry: 1.000 m cube.
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
cube = bpy.context.object
cube.name = "DCS_EDM_TEST_DARK_BLUE_CUBE_1M"
cube.dimensions = (1.0, 1.0, 1.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Create a current native Eagle Dynamics EDM material directly.
# This avoids the legacy "Green RW" reference-node migration path.
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
edm_node.label = "EDM Dark Blue Default"

base_color = edm_node.inputs.get("Base Color")
if base_color is None:
    raise RuntimeError("Native ED Default Material has no Base Color input.")
base_color.default_value = (0.02, 0.06, 0.20, 1.0)

base_alpha = edm_node.inputs.get("Base Alpha*")
if base_alpha is not None:
    base_alpha.default_value = 1.0

cube.data.materials.clear()
cube.data.materials.append(mat)

# Record explicit smoke-test metadata in the .blend artifact.
cube["TPG_EDM_SMOKE_TEST"] = True
cube["DIMENSION_METERS"] = 1.0
cube["COLOR_RGB"] = "0.02,0.06,0.20"
cube["EDM_SHADER_NODE_TYPE"] = edm_node.bl_idname

dims = tuple(round(v, 6) for v in cube.dimensions)
if dims != (1.0, 1.0, 1.0):
    raise RuntimeError(f"Cube dimensions are not exactly 1m: {dims}")
if edm_node.bl_idname != "EdmDefaultShaderNodeType":
    raise RuntimeError(f"Unexpected EDM node type: {edm_node.bl_idname}")

print(f"[TPG TEST] Cube dimensions: {dims}")
print(f"[TPG TEST] EDM material: {mat.name}")
print(f"[TPG TEST] Native EDM node type: {edm_node.bl_idname}")
print(f"[TPG TEST] Base Color: {tuple(base_color.default_value)}")
