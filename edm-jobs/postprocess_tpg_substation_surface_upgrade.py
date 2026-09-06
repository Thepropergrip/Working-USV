import bpy
from pathlib import Path

# Visual post-process for the LIGHTS edition only.
# - Deepens the buried foundation skirt so uneven terrain cannot expose a flat lower edge.
# - Uses the ground-bed material across the complete raised bed.
# - Applies meter-scaled box/world UV projection so supplied ground/brick textures tile
#   across long faces and around bends instead of being stretched once over each surface.
# - Adds placeholder normal-map slots whose image files are replaced in the final package
#   with the user's actual DirectX normal maps.

TEXDIR = Path(__import__('os').environ.get('GITHUB_WORKSPACE', '.')).resolve() / 'edm-artifacts' / 'Textures'
TEXDIR.mkdir(parents=True, exist_ok=True)


def ensure_flat_normal(material, texture_name):
    if material is None or not material.use_nodes:
        return
    group = material.node_tree.nodes.get('Group')
    if group is None:
        return
    try:
        from enums import NodeSocketInDefaultEnum
        normal_socket = group.inputs[NodeSocketInDefaultEnum.NORMAL]
    except Exception:
        return

    path = TEXDIR / texture_name
    if not path.exists():
        img = bpy.data.images.new(texture_name, width=8, height=8, alpha=True)
        img.pixels = [0.5, 0.5, 1.0, 1.0] * 64
        img.filepath_raw = str(path)
        img.file_format = 'PNG'
        img.save()
    tex = material.node_tree.nodes.new('ShaderNodeTexImage')
    tex.name = texture_name + '_NODE'
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    tex.image.colorspace_settings.name = 'Non-Color'
    material.node_tree.links.new(tex.outputs['Color'], normal_socket)


def planar_tile_uv(obj, meters_per_tile=3.0):
    if obj is None or obj.type != 'MESH':
        return
    mesh = obj.data
    uv = mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
    s = 1.0 / max(0.01, meters_per_tile)
    # Project each face along its dominant normal axis. This keeps texture density
    # constant on tops, sides, slopes and bevels instead of stretching at edges.
    for poly in mesh.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            if ax == 2:      # top/bottom -> XY
                u, v = co.x * s, co.y * s
            elif ax == 1:    # front/back -> XZ
                u, v = co.x * s, co.z * s
            else:            # left/right -> YZ
                u, v = co.y * s, co.z * s
            uv.data[li].uv = (u, v)


# Material handles created by tpg_substation_common.mats() and the user-asset upgrade.
ground_mat = bpy.data.materials.get('TPG_SUB100_Gravel')
brick_mat = bpy.data.materials.get('TPG_SUB100_UtilityBrick')
xfmr_user_mat = bpy.data.materials.get('TPG_USER_Transformer')
panel_user_mat = bpy.data.materials.get('TPG_USER_ControlPanel')
ensure_flat_normal(ground_mat, 'TPG_SUB100_Gravel_Normal.png')
ensure_flat_normal(brick_mat, 'TPG_SUB100_UtilityBrick_Normal.png')
ensure_flat_normal(xfmr_user_mat, 'TPG_USER_Transformer_Normal.png')
ensure_flat_normal(panel_user_mat, 'TPG_USER_ControlPanel_Normal.png')

# Ground bed: use one continuous real ground material and push the buried skirt much
# farther below grade. The foundation builder emits three equal-size rings: top, toe,
# buried skirt. Only the lowest ring is moved; visible yard elevation/layout is unchanged.
foundation = bpy.data.objects.get('FOUNDATION_BED')
if foundation and foundation.type == 'MESH':
    if ground_mat:
        foundation.data.materials.clear()
        foundation.data.materials.append(ground_mat)
    zs = sorted({round(v.co.z, 5) for v in foundation.data.vertices})
    if zs:
        lowest = zs[0]
        for v in foundation.data.vertices:
            if abs(v.co.z - lowest) < 1e-4:
                v.co.z = min(v.co.z, -1.65)
    planar_tile_uv(foundation, meters_per_tile=3.2)

# The entire raised top cap gets the same supplied ground texture, tiled at a realistic
# scale rather than stretched across the 120 x 90 m yard.
yard = bpy.data.objects.get('YARD_GRAVEL')
if yard:
    if ground_mat:
        yard.data.materials.clear()
        yard.data.materials.append(ground_mat)
    planar_tile_uv(yard, meters_per_tile=3.2)

# Main relay/control building gets the user's brick set with meter-scaled projection.
# Beveled edges are independently projected by face normal, avoiding smeared corners.
ctrl = bpy.data.objects.get('CTRL_BUILDING')
if ctrl:
    if brick_mat:
        ctrl.data.materials.clear()
        ctrl.data.materials.append(brick_mat)
    planar_tile_uv(ctrl, meters_per_tile=2.0)

# User-supplied transformer/control-panel textures are atlas-style assets. Apply a
# moderate world-projected density to the procedural replacement geometry so the PBR
# weathering/detail reads consistently instead of stretching over an entire transformer.
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or not obj.data.materials:
        continue
    names = {m.name for m in obj.data.materials if m}
    if 'TPG_USER_Transformer' in names:
        planar_tile_uv(obj, meters_per_tile=2.4)
    elif 'TPG_USER_ControlPanel' in names:
        planar_tile_uv(obj, meters_per_tile=1.0)

print('TPG surface upgrade applied: deep foundation skirt, tiled ground/brick/user assets, normal-map slots')