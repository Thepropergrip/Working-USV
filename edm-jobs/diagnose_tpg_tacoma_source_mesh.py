import bpy
from collections import defaultdict
body=bpy.data.objects.get('FBX_Plane.001')
if body is None or body.type!='MESH': raise RuntimeError('Missing FBX_Plane.001')
vs=list(body.data.vertices)
xs=[v.co.x for v in vs]; ys=[v.co.y for v in vs]; zs=[v.co.z for v in vs]
print('[TPG SOURCE BOUNDS]', 'count',len(vs),'x',min(xs),max(xs),'y',min(ys),max(ys),'z',min(zs),max(zs))
for cutoff in (0.5,0.7,0.9,1.1,1.3,1.5):
    q=[v for v in vs if v.co.z>=cutoff]
    if q:
        print('[TPG SOURCE HIGH]',cutoff,'count',len(q),'x',min(v.co.x for v in q),max(v.co.x for v in q),'y',min(v.co.y for v in q),max(v.co.y for v in q),'z',min(v.co.z for v in q),max(v.co.z for v in q))
# spatial bins for upper half of source body
bins=defaultdict(list)
for v in vs:
    if v.co.z>=0.7:
        xb=round(v.co.x*2)/2
        bins[xb].append(v)
for xb in sorted(bins):
    q=bins[xb]
    print('[TPG SOURCE XBIN]',xb,'count',len(q),'z',min(v.co.z for v in q),max(v.co.z for v in q),'absYmax',max(abs(v.co.y) for v in q))
# highest vertices give direct roof/cab coordinates
for v in sorted(vs,key=lambda v:v.co.z,reverse=True)[:40]:
    print('[TPG SOURCE TOP]',round(v.co.x,4),round(v.co.y,4),round(v.co.z,4))
