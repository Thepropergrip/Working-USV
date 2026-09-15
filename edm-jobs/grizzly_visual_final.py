"""Final visual-only repair on top of the unchanged approved animation build."""
import bpy, json, os
from pathlib import Path
from mathutils import Vector
root = Path(os.environ['GITHUB_WORKSPACE'])
audit = root / 'edm-jobs' / 'grizzly_visual_audit.py'
# Geometry repair and frozen-rig validation, without re-downloading offline tools.
text = audit.read_text(encoding='utf-8').split('# Optional validation tools/reference acquisition.')[0]
ns = {'__name__': '__main__'}
exec(compile(text, str(audit), 'exec'), ns)
lock = ns['freeze']()
# Remove the obsolete pseudo-stencil bars from the exterior. Keep their object
# transforms, hierarchy and node inventory intact; recess only their vertices
# inside the enclosure. These are the old decorative bars, not printed labels.
recessed = []
for o in bpy.data.objects:
    if o.name.startswith('DoorStencil_') and o.type == 'MESH':
        inv = o.matrix_world.inverted()
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            p.x -= 1.4
            v.co = inv @ p
        o.data.update()
        recessed.append(o.name)
# Restore source-printed plaque artwork rather than black placeholder faces.
for name, matname in [('CSC_DataPlate', 'GRZVU02_label'), ('CSC_DataPlateInset', 'GRZVU02_label'), ('HazardPlate', 'GRZVU02_warning')]:
    o = bpy.data.objects.get(name)
    if o is None: raise RuntimeError('Missing expected label plaque: ' + name)
    o.data.materials.clear(); o.data.materials.append(bpy.data.materials[matname])
    b = ns['bounds'](o)
    if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')
    uv = o.data.uv_layers.active.data
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            p = o.matrix_world @ o.data.vertices[o.data.loops[li].vertex_index].co
            u = (p.y - b[1][0]) / (b[1][1] - b[1][0])
            v = (p.z - b[2][0]) / (b[2][1][1] - b[2][0]) if False else (p.z - b[2][0]) / (b[2][1] - b[2][0])
            uv[li].uv = (.005 + .990*u, .005 + .990*v)
if ns['freeze']() != lock: raise RuntimeError('Final visual cleanup changed locked rig')
out = root / 'edm-artifacts'
p = out / 'grizzly_visual_repair_validation.json'
report = json.loads(p.read_text())
report['obsolete_pseudo_stencils_recessed'] = recessed
report['printed_plaque_uvs_restored'] = ['CSC_DataPlate', 'CSC_DataPlateInset', 'HazardPlate']
report['final_rig_equal'] = True
p.write_text(json.dumps(report, indent=2))
(out / 'grizzly_object_audit_after.json').write_text(json.dumps(ns['audit'](), indent=2))
bpy.context.scene.frame_set(100); bpy.context.view_layer.update()
print('GRIZZLY_FINAL_VISUAL_REPAIR_PASS; ALL APPROVED ANIMATIONS AND CONNECTORS UNCHANGED', flush=True)
