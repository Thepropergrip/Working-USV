from pathlib import Path

p=Path('edm-jobs/build_tpg_tacoma.py')
src=p.read_text(encoding='utf-8')

def swap(name,next_name,new_body):
    global src
    a=src.index('\ndef '+name+'(')+1
    b=src.index('\ndef '+next_name+'(',a)
    src=src[:a]+new_body.rstrip()+'\n\n'+src[b:]

swap('tube','text_obj',r'''def tube(name,pts,r,ma):
    c=bpy.data.curves.new(name+'C','CURVE');c.dimensions='3D';c.bevel_depth=r;c.bevel_resolution=2
    s=c.splines.new('POLY');s.points.add(len(pts)-1)
    for p,co in zip(s.points,pts):p.co=(*co,1)
    o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);c.materials.append(ma)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    try:bpy.ops.object.convert(target='MESH')
    except:pass
    return bpy.context.view_layer.objects.active''')

swap('text_obj','anim_rot',r'''def text_obj(txt,name,loc,size,ma,rot=(math.pi/2,0,0),extrude=.003):
    c=bpy.data.curves.new(name+'C','FONT');c.body=txt;c.align_x='CENTER';c.align_y='CENTER';c.size=size;c.extrude=extrude;c.bevel_depth=.0008
    o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=rot;c.materials.append(ma)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    try:bpy.ops.object.convert(target='MESH')
    except:pass
    return bpy.context.view_layer.objects.active''')

swap('add_base','add_custom',r'''def add_base():
    z,meta=payload(); mapping={'body':M['paint'],'black':M['black'],'plastic':M['black'],'glass':M['glass'],'front light':M['lamp'],'back light ':M['red'],'Material.007':M['rim'],'Material.008':M['brake'],'Material.009':M['rubber']}
    targets={'Cylinder':(1.7855,-.820,.405),'Cylinder.001':(-1.7855,-.820,.405),'Cylinder.002':(1.7855,.820,.405),'Cylinder.003':(-1.7855,.820,.405)}
    wheel_objs=[]
    for info in meta['geometries']:
        n=info['name'];v=z[n+'_v'].astype(float);f=faces(z[n+'_p']);srcm=info['materials'];mats=[mapping.get(x,M['black']) for x in srcm];mi=z[n+'_mat']
        if DESTROYED and n=='Plane.001':mats=[M['burnt'] if x==mapping.get('body') else x for x in mats]
        o=mesh('FBX_'+n,v,f,mats,mi)
        if n in targets:
            xs=[q.co.x for q in o.data.vertices];ys=[q.co.y for q in o.data.vertices];zs=[q.co.z for q in o.data.vertices]
            c=((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2);t=targets[n];d=(t[0]-c[0],t[1]-c[1],t[2]-c[2])
            for q in o.data.vertices:q.co.x+=d[0];q.co.y+=d[1];q.co.z+=d[2]
            wheel_objs.append(o);print(f'[TPG TACOMA] wheel {n}: {c} -> {t}')
        if LOD:
            dec=o.modifiers.new('LOD','DECIMATE');dec.ratio=.55 if LOD==1 else .28;bpy.context.view_layer.objects.active=o
            try:bpy.ops.object.modifier_apply(modifier=dec.name)
            except:pass
    for o in wheel_objs:
        xs=[q.co.x for q in o.data.vertices];ys=[q.co.y for q in o.data.vertices];zs=[q.co.z for q in o.data.vertices];c=((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2)
        steer=bpy.data.objects.new(o.name+'_STEER',None);steer.location=c;bpy.context.collection.objects.link(steer)
        roll=bpy.data.objects.new(o.name+'_ROLL',None);roll.location=c;bpy.context.collection.objects.link(roll);parent_keep(roll,steer);parent_keep(o,roll)
        anim_rot(roll,8,1,-2*math.pi,2*math.pi)
        if c[0]>0:anim_rot(steer,9,2,math.radians(-30),math.radians(30))''')

swap('add_custom','destroyed',r'''def add_custom():
    p=M['burnt'] if DESTROYED else M['paint']
    # Cap shell: tapered front/rear and crowned roof instead of a floating rectangular block.
    prof=[(-.96,1.04),(-.90,1.66),(-1.04,1.76),(-2.55,1.75),(-2.78,1.66),(-2.84,1.04)];yy=.855;vv=[]
    for y in (-yy,yy):
        for x,z in prof:vv.append((x,y,z))
    nn=len(prof);ff=[tuple(range(nn)),tuple(range(nn,2*nn))]
    for i in range(nn):j=(i+1)%nn;ff.append((i,j,nn+j,nn+i))
    mesh('CAMPER_SHELL',vv,ff,[p])
    for s in (-1,1):box(f'CAMPER_SIDE_GLASS_{s}',(-1.85,s*.861,1.47),(1.30,.016,.36),M['glass'],.035)
    box('CAMPER_REAR_GLASS',(-2.845,0,1.44),(.014,1.38,.38),M['glass'],.028)
    # Low profile cab + shell racks with actual feet.
    for ri,(cx,l,z) in enumerate(((.22,1.42,1.855),(-1.84,1.46,1.825))):
        for s in (-1,1):
            box(f'RACK_RAIL_{ri}_{s}',(cx,s*.73,z),(l,.055,.055),M['metal'],.010)
            for fx in (cx-l*.40,cx+l*.40):box(f'RACK_FOOT_{ri}_{s}_{fx:.2f}',(fx,s*.70,z-.065),(.10,.08,.10),M['metal'],.012)
        cnt=7 if LOD==0 else 4
        for i in range(cnt):
            x=cx-l*.43+i*l*.86/(cnt-1);box(f'RACK_BAR_{ri}_{i}',(x,0,z),(.035,1.42,.030),M['metal'],.005)
    # Black Oak forward-facing cowl pods + mesh brackets.
    for s in (-1,1):
        x=1.09;y=s*.885;z=1.49;tube(f'DITCH_BRACKET_{s}',[(1.02,s*.77,1.31),(1.05,s*.83,1.40),(1.08,y,1.43)],.016,M['metal']);box(f'BLACK_OAK_{s}',(x,y,z),(.16,.18,.16),M['metal'],.022)
        for dy in (-.035,.035):
            for dz in (-.035,.035):cyl(f'BLACK_OAK_LED_{s}_{dy}_{dz}',(x+.086,y+dy,z+dz),.019,.010,M['lamp'],12,rot=(0,math.pi/2,0))
        if LOD==0:
            for i in range(6):box(f'BLACK_OAK_FIN_{s}_{i}',(x-.083-i*.012,y,z),(.008,.184,.152),M['black'],.001)
    # Real tube sliders, now baked to meshes for EDM export.
    for s in (-1,1):
        tube(f'SLIDER_MAIN_{s}',[(-1.05,s*.99,.42),(1.02,s*.99,.42)],.038,M['metal']);tube(f'SLIDER_INNER_{s}',[(-1.00,s*.88,.42),(.98,s*.88,.42)],.029,M['metal'])
        for x in (-.75,-.20,.40,.88):tube(f'SLIDER_BRACE_{s}_{x}',[(x,s*.78,.39),(x,s*.97,.42)],.022,M['metal'])
    # Rear bumper shifted behind body shell, with amber reverse/auxiliary lamps.
    box('REAR_BUMPER',(-3.11,0,.62),(.20,1.86,.22),M['metal'],.030)
    for s in (-1,1):
        box(f'REAR_WING_{s}',(-3.10,s*.76,.67),(.22,.34,.24),M['metal'],.024);box(f'REAR_AMBER_{s}',(-3.215,s*.56,.68),(.015,.20,.085),M['amber'],.010);torus(f'RECOVERY_{s}',(-3.22,s*.32,.49),.058,.014,M['metal'],rot=(0,math.pi/2,0))
    box('REAR_PLATE',(-3.218,0,.71),(.014,.31,.152),M['white'],.008);text_obj('DCS 4X4','REAR_PLATE_TEXT',(-3.228,0,.71),.050,M['blue'],rot=(math.pi/2,0,-math.pi/2),extrude=.002)
    if LOD==0:
        for s in (-1,1):
            rr=(math.pi/2,0,0) if s<0 else (-math.pi/2,0,math.pi)
            text_obj('TACOMA',f'TACOMA_BADGE_{s}',(.52,s*.955,1.00),.060,M['black'],rr,extrude=.002)
            text_obj('TRD 4X4',f'TRD_BADGE_{s}',(-2.08,s*.956,1.26),.050,M['black'],rr,extrude=.002)
            text_obj('OFF ROAD',f'OFFROAD_{s}',(-2.08,s*.957,1.20),.026,M['black'],rr,extrude=.001)''')

swap('collision','build',r'''def collision():
    box('COLLISION_MAIN',(0,0,1.0),(4.65,1.72,1.30),None,0,coll=True)
    box('COLLISION_NOSE',(2.30,0,.88),(1.15,1.75,.85),None,0,coll=True)
    box('COLLISION_REAR',(-2.42,0,1.03),(1.45,1.78,1.42),None,0,coll=True)''')

exec(compile(src,str(p),'exec'),globals(),globals())
