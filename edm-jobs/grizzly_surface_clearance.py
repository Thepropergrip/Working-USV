"""Final visual QA: separate coincident lid-skin and fixed hinge end faces.
Animation curves, pivots, object transforms and connector positions are untouched.
"""
import bpy, json, os, runpy
from pathlib import Path
root = Path(os.environ['GITHUB_WORKSPACE'])
ctx = runpy.run_path(str(root / 'edm-jobs/grizzly_visual_final.py'), run_name='__main__')
helpers = ctx['ns']
locked = helpers['freeze']()
changes = []
# The small aft skin intersects both long skins at precisely the same plane
# when lowered, producing black/z-fighting rectangles in the exported model.
# Recess its mesh surface by 1 mm only. Do not move its object or pivot.
o = bpy.data.objects['Roof_Aft']
before = helpers['bounds'](o)
for v in o.data.vertices:
    v.co.z -= .001
# It is only vertex-space geometry; the complete approved action is unchanged.
o.data.update()
changes.append({'object':o.name, 'before':before, 'after':helpers['bounds'](o), 'reason':'1 mm skin separation; pivot and animation unchanged'})
# The fixed hinge beams also shared the long lids' exact vertical end planes.
# Inset the stationary endcaps by 2 mm; hinge pins and all moving parts stay put.
for name in ('Roof_Port_HingeBeam','Roof_Starboard_HingeBeam'):
    o=bpy.data.objects[name]
    before=helpers['bounds'](o)
    helpers['world_axis'](o,0,before[0][0]+.002,before[0][1]-.002)
    changes.append({'object':name,'before':before,'after':helpers['bounds'](o),'reason':'fixed endcaps inset 2 mm to remove coincident faces'})
if helpers['freeze']() != locked:
    raise RuntimeError('Surface clearance changed locked animation or connector data')
out=root/'edm-artifacts'
p=out/'grizzly_visual_repair_validation.json'
r=json.loads(p.read_text());r['coincident_surface_clearance']=changes;r['final_rig_equal']=True
p.write_text(json.dumps(r,indent=2))
(out/'grizzly_object_audit_after.json').write_text(json.dumps(helpers['audit'](),indent=2))
bpy.context.scene.frame_set(100);bpy.context.view_layer.update()
print('GRIZZLY_SURFACE_CLEARANCE_PASS; APPROVED ANIMATIONS AND CONNECTORS UNCHANGED',flush=True)
