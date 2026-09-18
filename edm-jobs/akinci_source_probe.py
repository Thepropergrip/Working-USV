from __future__ import annotations
import json, os, re, urllib.request, urllib.error
from pathlib import Path
import bpy

UID="6888b15081a8436f83baf35f5e0d50ed"
workspace=Path(os.environ["GITHUB_WORKSPACE"])
out=workspace/"edm-artifacts"; out.mkdir(exist_ok=True)
urls=[
 f"https://api.sketchfab.com/v3/models/{UID}",
 f"https://sketchfab.com/i/models/{UID}",
 f"https://sketchfab.com/models/{UID}/embed?autostart=1&internal=1&tracking=0",
 f"https://api.sketchfab.com/v3/models/{UID}/download",
]
records=[]
for url in urls:
    rec={"url":url}
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"*/*"})
        with urllib.request.urlopen(req,timeout=60) as r:
            data=r.read(2_000_000)
            rec["status"]=getattr(r,"status",200)
            rec["final_url"]=r.geturl()
            rec["headers"]=dict(r.headers.items())
            txt=data.decode("utf-8","replace")
            rec["sample"]=txt[:20000]
            rec["urls_found"]=re.findall(r'https?://[^"\\s<>]+',txt)[:200]
    except Exception as e:
        rec["error"]=repr(e)
    records.append(rec)
(out/"sketchfab_probe.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
# keep exporter happy
bpy.ops.mesh.primitive_cube_add(size=1.0)
bpy.context.object.name="AKINCI_SOURCE_PROBE"
print("AKINCI_SOURCE_PROBE_DONE")
