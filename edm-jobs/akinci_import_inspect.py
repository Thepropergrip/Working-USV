from __future__ import annotations
import json, os, pathlib, shutil, subprocess, sys
from pathlib import Path
import bpy
from mathutils import Vector

UID="6888b15081a8436f83baf35f5e0d50ed"
W=Path(os.environ["GITHUB_WORKSPACE"])
ART=W/"edm-artifacts"; ART.mkdir(exist_ok=True)
CLI=W/"_sketchfab_cli"
DL=W/"_akinci_download"
if CLI.exists(): shutil.rmtree(CLI)
if DL.exists(): shutil.rmtree(DL)
subprocess.run(["git","clone","--depth","1","https://github.com/seryi882/sketchfab-cli.git",str(CLI)],check=True)
py=shutil.which("python") or shutil.which("python3")
if not py: raise RuntimeError("Runner Python not found")
subprocess.run([py,"-m","pip","install","-q","-r",str(CLI/"requirements.txt")],check=True)
subprocess.run([py,str(CLI/"main.py"),"-q","-o",str(DL),UID],check=True,cwd=str(CLI))
gltfs=list(DL.rglob("*.gltf"))
if not gltfs: raise RuntimeError("No glTF produced")
gltf=gltfs[0]
print("AKINCI_GLTF",gltf)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(gltf))
bpy.context.view_layer.update()
records=[]
for o in bpy.context.scene.objects:
    if o.type!="MESH": continue
    pts=[o.matrix_world @ Vector(c) for c in o.bound_box]
    lo=[min(p[i] for p in pts) for i in range(3)]
    hi=[max(p[i] for p in pts) for i in range(3)]
    records.append({
      "name":o.name,"verts":len(o.data.vertices),"faces":len(o.data.polygons),
      "materials":[s.material.name if s.material else None for s in o.material_slots],
      "min":lo,"max":hi,"dims":[hi[i]-lo[i] for i in range(3)],
      "center":[(hi[i]+lo[i])/2 for i in range(3)]
    })
(ART/"akinci_scene_inventory.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
# Copy gltf package to artifact for exact inspection/reuse.
dst=ART/"source_gltf"
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(gltf.parent,dst)
# Export a mesh-name text summary
with (ART/"akinci_scene_inventory.txt").open("w",encoding="utf-8") as f:
    for r in sorted(records,key=lambda x:x["name"]):
        f.write(f'{r["name"]} verts={r["verts"]} faces={r["faces"]} center={r["center"]} dims={r["dims"]} mats={r["materials"]}\n')
# Clear imported scene so the EDM export is only a harmless probe cube.
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=1)
bpy.context.object.name="AKINCI_IMPORT_PROBE"
print("AKINCI_IMPORT_INSPECTION_DONE",len(records))
