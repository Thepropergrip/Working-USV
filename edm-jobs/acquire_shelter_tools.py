# Retrieve public build dependencies so the supplied model can be processed locally.
# No source assets, credentials or personal data are uploaded by this job.
import os, sys, json, shutil, hashlib, urllib.request, lzma, zipfile, concurrent.futures
from pathlib import Path
import bpy
w=Path(os.environ['GITHUB_WORKSPACE']); out=w/'edm-artifacts'; out.mkdir(exist_ok=True)
manifest=[]
def fetch(url, dest):
    dest=Path(dest)
    req=urllib.request.Request(url, headers={'User-Agent':'TPG-DCS-Asset-Build/1.0'})
    with urllib.request.urlopen(req, timeout=180) as src, dest.open('wb') as dst:
        shutil.copyfileobj(src,dst)
    h=hashlib.sha256(dest.read_bytes()).hexdigest()
    manifest.append({'url':url,'file':dest.name,'bytes':dest.stat().st_size,'sha256':h})
    print('ACQUIRED',dest.name,dest.stat().st_size,flush=True)
    return dest
# Public Debian package metadata determines exact package files rather than guessed versions.
idx=fetch('https://deb.debian.org/debian/dists/trixie/main/binary-amd64/Packages.xz',out/'Packages.xz')
packages={}
for block in lzma.decompress(idx.read_bytes()).decode().split('\n\n'):
    d={}
    for ln in block.splitlines():
        if ': ' in ln and not ln.startswith(' '):
            k,v=ln.split(': ',1);d[k]=v
    if 'Package' in d: packages[d['Package']]=d
wanted=['wine64','wine','libwine','libcapi20-3t64','libgphoto2-6','libgphoto2-port12','libpcap0.8t64','libasound2t64','libosmesa6','libldap2','libpulse0','libunwind8','libusb-1.0-0','libv4l-0t64','libv4lconvert0t64','libsane1','libavif16','libaom3','libdav1d7','libyuv0','libgstreamer-plugins-base1.0-0','libgstreamer1.0-0','liborc-0.4-0t64']
debs=out/'debs';debs.mkdir(exist_ok=True)
tasks=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    tasks.append(ex.submit(fetch,'https://download.blender.org/release/Blender4.1/blender-4.1.1-linux-x64.tar.xz',out/'blender-linux.tar.xz'))
    for n in wanted:
        if n in packages:
            d=packages[n]; tasks.append(ex.submit(fetch,'https://deb.debian.org/debian/'+d['Filename'],debs/Path(d['Filename']).name))
    for t in tasks:t.result()
# The workflow has already downloaded this official portable Windows Blender ZIP.
winzip=Path(os.environ['RUNNER_TEMP'])/'blender-4.1.1.zip'
shutil.copyfile(winzip,out/'blender-windows.zip')
addon=Path(os.environ['BLENDER_USER_SCRIPTS'])/'addons'/'io_scene_edm'
with zipfile.ZipFile(out/'edm-addon.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in addon.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:z.write(p, p.relative_to(addon.parent).as_posix())
shutil.copyfile(w/'edm-jobs'/'build_nato_shelter.py',out/'previous_shelter_builder.py')
shutil.copyfile(w/'tools'/'dcs-edm'/'export_job.py',out/'export_job.py')
(out/'dependency_manifest.json').write_text(json.dumps(manifest,indent=2))
(out/'debian_packages.json').write_text(json.dumps({n:packages.get(n) for n in wanted},indent=2))
idx.unlink()
# This EDM is an explicitly named tools self-test, not the aircraft shelter.
bpy.ops.mesh.primitive_cube_add(size=1)
bpy.context.object.name='TOOLING_SELFTEST_NOT_SHELTER'
print('SHELTER_TOOLS_ACQUIRED',flush=True)
