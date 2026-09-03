import base64,zlib,json,os,sys,runpy
from pathlib import Path
workspace=Path(os.environ.get("GITHUB_WORKSPACE",os.getcwd()))
parts=[(workspace/"edm-jobs"/f"magura360_payload_{i}.txt").read_text(encoding="utf-8").strip() for i in range(1,5)]
files=json.loads(zlib.decompress(base64.b64decode("".join(parts))).decode())
root=workspace/"edm-jobs"/"_magura360_runtime"
script_dir=root/"blender"
script_dir.mkdir(parents=True,exist_ok=True)
for name,content in files.items(): (script_dir/name).write_text(content,encoding="utf-8")
sys.path.insert(0,str(script_dir))
for stage in ("01_scene_setup.py","02_import_or_model.py","02b_raise_turret.py","03_materials.py","04_damage_and_collision.py","05_connectors_and_args.py"):
    runpy.run_path(str(script_dir/stage),run_name="__main__")
from magura_common import INTACT_LODS,DESTROYED_LODS,SUPPORT_COLLECTIONS,PREVIEW_COLLECTION,set_collection_visible
set_collection_visible(PREVIEW_COLLECTION,False)
for n in DESTROYED_LODS: set_collection_visible(n,False)
for n in INTACT_LODS+SUPPORT_COLLECTIONS: set_collection_visible(n,True)
print("MAGURA360_SCENE_READY=1")
