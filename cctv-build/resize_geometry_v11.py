"""TPG CCTV proportion correction; input/output Blender Z-up metres."""
import numpy as np
RANGES=[[0,67],[67,375],[375,487],[487,607],[607,865],[865,999],[999,1457],[1457,1723],[1723,2031],[2031,2143],[2143,2263],[2263,2521],[2521,2655],[2655,2963],[2963,3071],[3071,3187],[3187,3451],[3451,3585],[3585,3857],[3857,4315],[4315,4773],[4773,4865],[4865,4957],[4957,5049],[5049,5163],[5163,5221],[5221,5541],[5541,5655],[5655,5712],[5712,6192],[6192,6384],[6384,6498],[6498,6556],[6556,6568],[6568,7024],[7024,7088],[7088,7360],[7360,7840],[7840,7852],[7852,8308],[8308,8372],[8372,8852],[8852,8864],[8864,9320],[9320,9384],[9384,9576],[9576,9768],[9768,10584],[10584,11040],[11250,11838],[11838,12426],[12426,13110],[11040,11250],[13110,13174],[13174,13238],[13238,13302],[13302,13574],[13574,13646],[13646,14350],[14350,15054],[15054,15758]]
GROUPS={'camera_front':[1,2,3,4,5,6,21,29,30,31,32,33,34,35,36,53,58],
'camera_right':[8,9,10,11,12,18,19,22,27,28,37,38,39,40,45,54,59],
'camera_left':[13,14,15,16,17,20,23,24,25,41,42,43,44,46,55,56,60],
'utility_box':[0,7,26,47]}

def idx_for(ids):
    return np.concatenate([np.arange(*RANGES[i]) for i in ids])

def ring_groups(v,f,a,b):
    tri=f[((f>=a)&(f<b)).all(1)]-a
    edges=np.unique(np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0)
    lens=np.linalg.norm(v[a:b][edges[:,0]]-v[a:b][edges[:,1]],axis=1)
    e=edges[lens<0.0148]
    parent=list(range(b-a))
    def root(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    for x,y in e:
        rx,ry=root(int(x)),root(int(y))
        if rx!=ry:parent[ry]=rx
    _,labels=np.unique([root(i) for i in range(b-a)],return_inverse=True)
    n=int(labels.max())+1
    assert np.all(np.bincount(labels)==12),(n,np.bincount(labels))
    ringedges=np.unique(np.sort(labels[edges],axis=1),axis=0)
    ringedges=ringedges[ringedges[:,0]!=ringedges[:,1]]
    adjacency={i:[] for i in range(n)}
    for x,y in ringedges:adjacency[x].append(y);adjacency[y].append(x)
    ends=[i for i in adjacency if len(adjacency[i])==1]
    assert len(ends)==2
    order=[];previous=-1;cur=ends[0]
    while True:
        order.append(cur)
        nxt=[i for i in adjacency[cur] if i!=previous]
        if not nxt:break
        previous,cur=cur,nxt[0]
    assert len(order)==n
    return [np.where(labels==i)[0]+a for i in order]

def rotation_between(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
    cross=np.cross(a,b);c=float(np.dot(a,b));s=np.linalg.norm(cross)
    if s<1e-10:return np.eye(3)
    k=np.array([[0,-cross[2],cross[1]],[cross[2],0,-cross[0]],[-cross[1],cross[0],0]])
    return np.eye(3)+k+k@k*((1-c)/(s*s))

def resize(v,f):
    assert v.shape==(15758,3) and f.shape==(31085,3)
    original=v.copy().astype(float);v=original.copy()
    normal_matrices=np.tile(np.eye(3),(len(v),1,1));assigned=set()
    def bounds(ids):
        pts=original[idx_for(ids)];return pts.min(0),pts.max(0)
    shaft=original[idx_for([52])]
    oldhalf=float(np.max(np.abs(shaft[np.abs(shaft[:,2]-3.3628)<.0002,:2])))
    newhalf=oldhalf*.47
    transforms={};group_report={}
    for name,ids in GROUPS.items():
        if name=='camera_front':a=np.array([0,oldhalf,3.67165]);factor=.40
        elif name=='camera_right':a=np.array([oldhalf,0,4.4000]);factor=.40
        elif name=='camera_left':a=np.array([-oldhalf,0,5.2252]);factor=.40
        else:
            mn,mx=bounds([0,7,26]);a=np.array([0,oldhalf,(mn[2]+mx[2])/2]);factor=.60
        dest=a.copy();dest[:2]*=.47
        inds=idx_for(ids)
        if name=='camera_left':dest[2]+=6.0-np.max((original[inds]-a)*factor+dest,axis=0)[2]
        transforms[name]=(a,dest,factor)
        v[inds]=(original[inds]-a)*factor+dest
        normal_matrices[inds]=np.eye(3)/factor
        assigned.update(ids)
        group_report[name]={'scale':factor,'anchor_old_m':a.tolist(),'anchor_new_m':dest.tolist(),'bounds_m':[v[inds].min(0).tolist(),v[inds].max(0).tolist()]}
    # Keep 6 m overall, with the upper bracket still seated against the shaft.
    upperbracket=v[idx_for([20,24,25])]
    shaft_oldtop=original[idx_for([52]),2].max()
    shaft_newtop=max(shaft_oldtop,float(upperbracket[:,2].max())+.045)
    extra=shaft_newtop-shaft_oldtop
    oldcapbottom=5.5795;stretchstart=3.3628
    def mast_transform(points):
        z=points[:,2]
        # The base, gussets and shaft share one source mesh. Reshape separately.
        s=np.where(z<=.0399,.60,np.where(z<.2598,.60-(z-.0399)/(.2598-.0399)*.13,.47))
        r=np.max(np.abs(points[:,:2]),axis=1)
        capscale=.47+.13*np.clip((r-.1846)/(.2313-.1846),0,1)
        s=np.where(z>=oldcapbottom,capscale,s)
        out=points.copy();out[:,:2]*=s[:,None]
        out[:,2]+=extra*np.clip((z-stretchstart)/(oldcapbottom-stretchstart),0,1)
        return out
    for oid in [52,57]:
        inds=idx_for([oid]);pts=original[inds]
        v[inds]=mast_transform(pts)
        eps=1e-5;jac=np.empty((len(inds),3,3))
        for k in range(3):
            dv=np.zeros(3);dv[k]=eps
            jac[:,:,k]=(mast_transform(pts+dv)-mast_transform(pts-dv))/(2*eps)
        normal_matrices[inds]=np.linalg.inv(jac).transpose(0,2,1);assigned.add(oid)
    inds=idx_for([48]);v[inds,:2]*=.60
    normal_matrices[inds]=np.diag([1/.60,1/.60,1]);assigned.add(48)
    cables=[]
    for oid,cam,connector in [(49,'camera_left',56),(50,'camera_front',36),(51,'camera_right',18)]:
        a,b=RANGES[oid];rings=ring_groups(original,f,a,b)
        centers=np.array([original[i].mean(0) for i in rings])
        camcenter=original[idx_for([connector])].mean(0)
        if np.linalg.norm(centers[0]-camcenter)<np.linalg.norm(centers[-1]-camcenter):
            rings=rings[::-1];centers=centers[::-1]
        ba,bd,bs=transforms['utility_box'];ca,cd,cs=transforms[cam]
        start=(centers[0]-ba)*bs+bd;end=(centers[-1]-ca)*cs+cd
        length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(centers,axis=0),axis=1))]
        t=length/length[-1];loopscale=.48
        nc=start+(centers-centers[0])*loopscale+t[:,None]*(end-start-(centers[-1]-centers[0])*loopscale)
        # Route the slimmed tubes around the mast rather than through it.
        if oid==49:
            capweight=np.clip((nc[:,2]-5.60)/.15,0,1)
            nc[:,0]=np.minimum(nc[:,0],-.122-.05*capweight)
            clear=np.clip((nc[:,2]-5.48)/.16,0,1)*np.clip((5.94-nc[:,2])/.12,0,1)
            nc[:,1]=np.where(clear>0,np.maximum(nc[:,1],.092*clear-.06*(1-clear)),nc[:,1])
        elif oid==50:nc[:,1]=np.maximum(nc[:,1],.122)
        else:nc[:,0]=np.maximum(nc[:,0],.122)
        nc[0]=start;nc[-1]=end
        for _ in range(3):nc[1:-1]=.25*nc[:-2]+.5*nc[1:-1]+.25*nc[2:]
        oldt=np.gradient(centers,axis=0);newt=np.gradient(nc,axis=0)
        for j,inds in enumerate(rings):
            rot=rotation_between(oldt[j],newt[j])
            v[inds]=nc[j]+(original[inds]-centers[j])@rot.T*.35
            normal_matrices[inds]=rot/.35
        assigned.add(oid)
        cables.append({'object':oid,'rings':len(rings),'diameter_scale':.35,'endpoint_transforms':['utility_box',cam],'new_start_m':start.tolist(),'new_end_m':end.tolist()})
    assert assigned==set(range(61))
    assert np.isfinite(v).all() and np.isfinite(normal_matrices).all()
    assert abs(v[:,2].max()-6)<1e-6 and abs(v[:,2].min())<1e-6
    measures={}
    for name,ids in [('utility_box',[0,7,26]),('camera_front_housing',[1,21,29,58]),('camera_right_housing',[8,22,37,59]),('camera_left_housing',[13,23,41,60])]:
        pts=v[idx_for(ids)]
        measures[name]={'xyz_dimensions_m':(pts.max(0)-pts.min(0)).tolist()}
    measures['shaft_width_m']=2*newhalf
    measures['base_plate_width_m']=float(np.ptp(v[idx_for([52]),0]))
    return v,normal_matrices,{'groups':group_report,'cables':cables,'dimensions':measures,'height_m':6.0,'upper_shaft_extension_m':extra,'source_objects':61}
