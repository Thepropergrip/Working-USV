from __future__ import annotations
import json, os, pathlib, shutil, subprocess, sys, traceback
from pathlib import Path
import bpy
from mathutils import Vector

UID="6888b15081a8436f83baf35f5e0d50ed"
W=Path(os.environ["GITHUB_WORKSPACE"])
ART=W/"edm-artifacts"; ART.mkdir(exist_ok=True)
CLI=W/"_sketchfab_cli"
DL=W/"_akinci_download"
logs=[]
def run(cmd,cwd=None):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
    logs.append({"cmd":cmd,"cwd":cwd,"returncode":p.returncode,"stdout":p.stdout[-50000:],"stderr":p.stderr[-50000:]})
    if p.returncode: raise RuntimeError(f"Command failed {p.returncode}: {cmd}")
    return p
try:
    if CLI.exists(): shutil.rmtree(CLI)
    if DL.exists(): shutil.rmtree(DL)
    run(["git","clone","--depth","1","https://github.com/seryi882/sketchfab-cli.git",str(CLI)])
    py=shutil.which("python") or shutil.which("python3")
    node=shutil.which("node")
    logs.append({"python":py,"node":node})
    if not py: raise RuntimeError("Runner Python not found")
    run([py,"-m","pip","install","-q","-r",str(CLI/"requirements.txt")])
    run([py,str(CLI/"main.py"),"--check-tools"],cwd=str(CLI))
    run([py,str(CLI/"main.py"),"-q","-o",str(DL),UID],cwd=str(CLI))
    gltfs=list(DL.rglob("*.gltf"))
    logs.append({"gltfs":[str(x) for x in gltfs]})
    if not gltfs: raise RuntimeError("No glTF produced")
    gltf=gltfs[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(gltf))
    bpy.context.view_layer.update()
    records=[]
    for o in bpy.context.scene.objects:
        if o.type!="MESH": continue
        pts=[o.matrix_world @ Vector(c) for c in o.bound_box]
        lo=[min(p[i] for p in pts) for i in range(3)]
        hi=[max(p[i] for p in pts) for i in range(3)]
        records.append({"name":o.name,"verts":len(o.data.vertices),"faces":len(o.data.polygons),
          "materials":[s.material.name if s.material else None for s in o.material_slots],
          "min":lo,"max":hi,"dims":[hi[i]-lo[i] for i in range(3)],
          "center":[(hi[i]+lo[i])/2 for i in range(3)]})
    (ART/"akinci_scene_inventory.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
    with (ART/"akinci_scene_inventory.txt").open("w",encoding="utf-8") as q:
        for r in sorted(records,key=lambda x:x["name"]):
            q.write(f'{r["name"]} verts={r["verts"]} faces={r["faces"]} center={r["center"]} dims={r["dims"]} mats={r["materials"]}\n')
    dst=ART/"source_gltf"
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(gltf.parent,dst)
    logs.append({"success":True,"objects":len(records)})
except Exception as e:
    logs.append({"success":False,"exception":repr(e),"traceback":traceback.format_exc()})
finally:
    (ART/"akinci_import_probe_log.json").write_text(json.dumps(logs,indent=2),encoding="utf-8")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=1)
    bpy.context.object.name="AKINCI_IMPORT_PROBE"
    print("AKINCI_IMPORT_PROBE_FINISHED")
