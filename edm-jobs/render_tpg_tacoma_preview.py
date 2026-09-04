import bpy, os, math
from pathlib import Path
from mathutils import Vector

root = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
outdir = root / "edm-artifacts"
outdir.mkdir(parents=True, exist_ok=True)


def dump_obj(frame, filename):
    bpy.context.scene.frame_set(frame)
    deps = bpy.context.evaluated_depsgraph_get()
    path = outdir / filename
    offset = 1
    with path.open("w", encoding="ascii", errors="ignore") as fp:
        fp.write("# TPG Tacoma QA mesh dump\n")
        fp.write(f"# Blender frame {frame}; EDM arg value {(frame/100.0)-1.0:.3f}\n")
        for obj in bpy.context.scene.objects:
            if obj.type != "MESH":
                continue
            if obj.name.startswith("COLLISION_") or obj.name.startswith("QA_"):
                continue
            ev = obj.evaluated_get(deps)
            mesh = ev.to_mesh()
            try:
                mesh.calc_loop_triangles()
                mw = ev.matrix_world
                fp.write(f"o {obj.name}\n")
                for v in mesh.vertices:
                    co = mw @ v.co
                    fp.write(f"v {co.x:.6f} {co.y:.6f} {co.z:.6f}\n")
                for tri in mesh.loop_triangles:
                    a,b,c = (idx + offset for idx in tri.vertices)
                    fp.write(f"f {a} {b} {c}\n")
                offset += len(mesh.vertices)
            finally:
                ev.to_mesh_clear()
    print(f"[TPG QA] {path} {path.stat().st_size} bytes")


def visible_bounds():
    pts=[]
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.name.startswith(('COLLISION_','QA_')):
            continue
        for c in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(c))
    if not pts:
        return Vector((-3,-1,0)), Vector((3,1,2))
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mn,mx


def look_at(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def ensure_qa_scene():
    scene=bpy.context.scene
    # GitHub Windows runners have no reliable OpenGL context in background mode.
    # Use Cycles CPU so visual QA is truly headless and cannot crash on WGL/Eevee init.
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=12
    scene.cycles.use_denoising=False
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.render.image_settings.color_mode='RGBA'
    scene.world.color=(0.055,0.060,0.065)

    # Remove only prior QA cameras/lights/ground; never touch exported truck objects.
    for o in list(bpy.data.objects):
        if o.name.startswith('QA_RENDER_'):
            bpy.data.objects.remove(o,do_unlink=True)

    cam_data=bpy.data.cameras.new('QA_RENDER_CAMERA_DATA')
    cam=bpy.data.objects.new('QA_RENDER_CAMERA',cam_data)
    scene.collection.objects.link(cam)
    scene.camera=cam
    cam_data.type='ORTHO'

    # Neutral matte ground plane for silhouette/readability. QA-only and not saved/exported.
    me=bpy.data.meshes.new('QA_RENDER_GROUND_MESH')
    ground=bpy.data.objects.new('QA_RENDER_GROUND',me)
    scene.collection.objects.link(ground)
    me.from_pydata([(-15,-15,0),(15,-15,0),(15,15,0),(-15,15,0)],[],[(0,1,2,3)])
    gm=bpy.data.materials.new('QA_RENDER_GROUND_MAT')
    gm.diffuse_color=(0.12,0.13,0.14,1)
    gm.use_nodes=True
    bsdf=gm.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value=(0.12,0.13,0.14,1)
        bsdf.inputs['Roughness'].default_value=0.88
    me.materials.append(gm)

    for i,(loc,energy,size) in enumerate([
        ((4.5,-5.0,7.5),1100,5.0),
        ((-4.0,4.0,5.0),850,4.0),
        ((0.0,0.0,9.0),700,5.5),
    ]):
        ld=bpy.data.lights.new(f'QA_RENDER_LIGHT_DATA_{i}','AREA')
        ld.energy=energy;ld.shape='DISK';ld.size=size
        lo=bpy.data.objects.new(f'QA_RENDER_LIGHT_{i}',ld)
        lo.location=loc;scene.collection.objects.link(lo)
        look_at(lo,(0,0,0.7))
    return cam


def render_views():
    bpy.context.scene.frame_set(100)
    cam=ensure_qa_scene()
    mn,mx=visible_bounds()
    center=(mn+mx)*0.5
    center.z=max(0.75,center.z)
    length=max(5.5,mx.x-mn.x); width=max(2.0,mx.y-mn.y); height=max(1.8,mx.z-mn.z)
    cam.data.ortho_scale=max(height*1.45,width*1.45,2.9)

    views={
        'side_driver':((0,-10,1.35),(0,0,1.0),max(height*1.45,2.75)),
        'front':((10,0,1.25),(0,0,0.95),max(width*1.55,2.7)),
        'rear':((-10,0,1.25),(0,0,0.95),max(width*1.55,2.7)),
        'front_3q':((8,-7,3.3),(0,0,0.9),max(length*.78,4.7)),
        'rear_3q':((-8,7,3.3),(0,0,0.9),max(length*.78,4.7)),
    }
    for name,(loc,target,scale) in views.items():
        cam.location=loc;cam.data.ortho_scale=scale;look_at(cam,target)
        path=outdir/f'TPG_Tacoma_Recon_QA_{name}.png'
        bpy.context.scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        if not path.exists() or path.stat().st_size < 10000:
            raise RuntimeError(f'QA render missing or too small: {path}')
        print(f'[TPG QA] rendered {path} {path.stat().st_size} bytes')

    # Steering-specific close side views to prove all front wheel visual detail follows arg 9.
    cam.location=(0,-10,1.15);cam.data.ortho_scale=max(height*1.35,2.65);look_at(cam,(0,0,0.85))
    for frame,name in ((0,'steer_left'),(200,'steer_right')):
        bpy.context.scene.frame_set(frame)
        path=outdir/f'TPG_Tacoma_Recon_QA_{name}.png'
        bpy.context.scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        if not path.exists() or path.stat().st_size < 10000:
            raise RuntimeError(f'QA steering render missing or too small: {path}')
        print(f'[TPG QA] rendered {path} {path.stat().st_size} bytes')
    bpy.context.scene.frame_set(100)


dump_obj(100, "TPG_Tacoma_Recon_QA_neutral.obj")
dump_obj(0, "TPG_Tacoma_Recon_QA_steer_left.obj")
dump_obj(200, "TPG_Tacoma_Recon_QA_steer_right.obj")
render_views()
bpy.context.scene.frame_set(100)
