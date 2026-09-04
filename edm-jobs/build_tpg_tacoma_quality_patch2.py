from pathlib import Path

p=Path('edm-jobs/build_tpg_tacoma_quality_patch.py')
src=p.read_text(encoding='utf-8')

a=src.index("swap('add_base','add_custom',r'''def add_base():")
b=src.index("\nswap('add_custom','destroyed'",a)
new="""swap('add_base','add_custom',r'''def add_base():
    z,meta=payload(); mapping={'body':M['paint'],'black':M['black'],'plastic':M['black'],'glass':M['glass'],'front light':M['lamp'],'back light ':M['red'],'Material.007':M['rim'],'Material.008':M['brake'],'Material.009':M['rubber']}
    targets={'Cylinder':(1.7855,-.820,.405),'Cylinder.001':(-1.7855,-.820,.405),'Cylinder.002':(1.7855,.820,.405),'Cylinder.003':(-1.7855,.820,.405)}
    wheel_objs=[]
    for info in meta['geometries']:
        n=info['name'];v=z[n+'_v'].astype(float);f=faces(z[n+'_p']);srcm=info['materials'];mats=[mapping.get(x,M['black']) for x in srcm];mi=z[n+'_mat']
        if DESTROYED and n=='Plane.001':mats=[M['burnt'] if x==mapping.get('body') else x for x in mats]
        o=mesh('FBX_'+n,v,f,mats,mi)
        if n in targets:
            xs=[q.co.x for q in o.data.vertices];ys=[q.co.y for q in o.data.vertices];zs=[q.co.z for q in o.data.vertices]
            c=((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2);t=targets[n]
            # Wheel data is centered locally; steering pivot carries the real axle/world position.
            for q in o.data.vertices:q.co.x-=c[0];q.co.y-=c[1];q.co.z-=c[2]
            wheel_objs.append((o,t));print(f'[TPG TACOMA] wheel {n}: source center {c} -> pivot {t}')
        if LOD:
            dec=o.modifiers.new('LOD','DECIMATE');dec.ratio=.55 if LOD==1 else .28;bpy.context.view_layer.objects.active=o
            try:bpy.ops.object.modifier_apply(modifier=dec.name)
            except:pass
    for o,t in wheel_objs:
        steer=bpy.data.objects.new(o.name+'_STEER',None);steer.location=t;bpy.context.collection.objects.link(steer)
        roll=bpy.data.objects.new(o.name+'_ROLL',None);roll.location=(0,0,0);roll.parent=steer;bpy.context.collection.objects.link(roll)
        o.location=(0,0,0);o.parent=roll
        anim_rot(roll,8,1,-2*math.pi,2*math.pi)
        if t[0]>0:anim_rot(steer,9,2,math.radians(-30),math.radians(30))''')"""
src=src[:a]+new+'\n'+src[b:]

# Smooth the cap shell edges rather than leaving the six-point polyhedron faceted.
src=src.replace("    mesh('CAMPER_SHELL',vv,ff,[p])", "    cap=mesh('CAMPER_SHELL',vv,ff,[p]);bm=cap.modifiers.new('CAP_SOFT','BEVEL');bm.width=.035;bm.segments=3 if LOD<2 else 1;bpy.context.view_layer.objects.active=cap\n    try:bpy.ops.object.modifier_apply(modifier=bm.name)\n    except:pass")
# TRD bedside marking belongs on the bed, not halfway up the cap.
src=src.replace("(-2.08,s*.956,1.26)","(-2.12,s*.956,.99)").replace("(-2.08,s*.957,1.20)","(-2.12,s*.957,.94)")

exec(compile(src,str(p),'exec'),globals(),globals())
