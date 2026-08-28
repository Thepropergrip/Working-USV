from pathlib import Path
import bpy
import io_scene_edm

# Exact test geometry: 1.000 m cube.
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
cube = bpy.context.object
cube.name = "DCS_EDM_TEST_DARK_BLUE_CUBE_1M"
cube.dimensions = (1.0, 1.0, 1.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Load Eagle Dynamics' own default EDM material from the pinned official exporter.
plugin_dir = Path(io_scene_edm.__file__).resolve().parent
reference_blend = plugin_dir / "Data" / "EDM_Default_Material.blend"
if not reference_blend.exists():
    raise FileNotFoundError(f"ED default material reference not found: {reference_blend}")

before = set(bpy.data.materials.keys())
with bpy.data.libraries.load(str(reference_blend), link=False) as (data_from, data_to):
    data_to.materials = list(data_from.materials)

loaded_names = [name for name in bpy.data.materials.keys() if name not in before]
mat = bpy.data.materials.get("EDM_Default_Material")
if mat is None and loaded_names:
    mat = bpy.data.materials.get(loaded_names[0])
if mat is None:
    raise RuntimeError("No material loaded from ED reference material blend.")

mat.name = "TPG_Dark_Blue_EDM"
mat.diffuse_color = (0.02, 0.06, 0.20, 1.0)

# Eagle Dynamics ships the reference material as the legacy "Green RW"
# node specifically so the add-on can migrate it to the current native EDM
# shader node. Run ED's own migration operator before setting export values.
update_result = bpy.ops.edm.import_matrials()
if update_result != {"FINISHED"}:
    raise RuntimeError(f"ED Update EDM Materials returned {update_result!r}")

# Set the converted ED Default Material's color value directly.
# No external texture is needed.
edm_node = None
for node in mat.node_tree.nodes:
    if getattr(node, "bl_idname", "") == "EdmDefaultShaderNodeType":
        edm_node = node
        break
    if hasattr(node, "inputs") and node.inputs.get("Base Color"):
        edm_node = node
        break

if edm_node is None:
    raise RuntimeError("EDM Default Material shader node was not found.")

base_color = edm_node.inputs.get("Base Color")
if base_color is None:
    raise RuntimeError("EDM Default Material has no Base Color input.")

# Dark blue, intentionally non-black so the EDM color block must contain a visible color.
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

dims = tuple(round(v, 6) for v in cube.dimensions)
if dims != (1.0, 1.0, 1.0):
    raise RuntimeError(f"Cube dimensions are not exactly 1m: {dims}")

print(f"[TPG TEST] Cube dimensions: {dims}")
print(f"[TPG TEST] EDM material: {mat.name}")
print(f"[TPG TEST] Base Color: {tuple(base_color.default_value)}")
