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
            if obj.type != "MESH" or obj.name.startswith(("COLLISION_", "QA_")):
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
                    a, b, c = (idx + offset for idx in tri.vertices)
                    fp.write(f"f {a} {b} {c}\n")
                offset += len(mesh.vertices)
            finally:
                ev.to_mesh_clear()
    print(f"[TPG QA] {path} {path.stat().st_size} bytes")


def visible_bounds():
    pts = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.name.startswith(("COLLISION_", "QA_")):
            continue
        for c in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(c))
    if not pts:
        return Vector((-3, -1, 0)), Vector((3, 1, 2))
    return (
        Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
        Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))),
    )


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def make_principled(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Roughness'].default_value = roughness
    return mat


def ensure_qa_scene():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.view_settings.exposure = -0.6

    # The previous dark QA environment swallowed the truck's black glass/rack/trim
    # and made the body look much flatter than the underlying FBX wire geometry.
    scene.world.color = (0.28, 0.29, 0.30)

    for o in list(bpy.data.objects):
        if o.name.startswith('QA_RENDER_'):
            bpy.data.objects.remove(o, do_unlink=True)

    cam_data = bpy.data.cameras.new('QA_RENDER_CAMERA_DATA')
    cam = bpy.data.objects.new('QA_RENDER_CAMERA', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam_data.type = 'ORTHO'

    me = bpy.data.meshes.new('QA_RENDER_GROUND_MESH')
    ground = bpy.data.objects.new('QA_RENDER_GROUND', me)
    scene.collection.objects.link(ground)
    me.from_pydata([(-15,-15,0),(15,-15,0),(15,15,0),(-15,15,0)], [], [(0,1,2,3)])
    me.materials.append(make_principled('QA_RENDER_GROUND_MAT', (0.20, 0.21, 0.22), 0.90))

    for i, (loc, energy, size) in enumerate([
        ((4.5,-5.0,7.5), 780, 5.0),
        ((-4.0,4.0,5.0), 560, 4.0),
        ((0.0,0.0,9.0), 420, 5.5),
    ]):
        ld = bpy.data.lights.new(f'QA_RENDER_LIGHT_DATA_{i}', 'AREA')
        ld.energy = energy
        ld.shape = 'DISK'
        ld.size = size
        lo = bpy.data.objects.new(f'QA_RENDER_LIGHT_{i}', ld)
        lo.location = loc
        scene.collection.objects.link(lo)
        look_at(lo, (0,0,0.7))

    clay = make_principled('QA_RENDER_CLAY_MAT', (0.42, 0.43, 0.45), 0.72)
    return cam, ground, clay


def render_one(cam, name, loc, target, scale):
    cam.location = loc
    cam.data.ortho_scale = scale
    look_at(cam, target)
    path = outdir / f'TPG_Tacoma_Recon_QA_{name}.png'
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if not path.exists() or path.stat().st_size < 10000:
        raise RuntimeError(f'QA render missing or too small: {path}')
    print(f'[TPG QA] rendered {path} {path.stat().st_size} bytes')


def render_views():
    scene = bpy.context.scene
    scene.frame_set(100)
    cam, ground, clay = ensure_qa_scene()
    mn, mx = visible_bounds()
    center = (mn + mx) * 0.5
    center.z = max(0.90, center.z)
    length = max(5.5, mx.x - mn.x)
    width = max(2.0, mx.y - mn.y)
    height = max(1.8, mx.z - mn.z)
    aspect = scene.render.resolution_x / scene.render.resolution_y

    # Orthographic scale is vertical. Side views must account for the 16:9
    # horizontal field or they crop the nose/tail and falsely make the body slab-like.
    side_scale = max(height * 1.55, (length / aspect) * 1.18, 3.70)
    front_scale = max(width * 1.55, height * 1.45, 2.90)
    q3_scale = max(length * 0.78, 4.80)

    views = {
        'side_driver': ((center.x, -10, 1.40), center, side_scale),
        'front': ((10, center.y, 1.35), center, front_scale),
        'rear': ((-10, center.y, 1.35), center, front_scale),
        'front_3q': ((8,-7,3.3), center, q3_scale),
        'rear_3q': ((-8,7,3.3), center, q3_scale),
    }
    for name, (loc, target, scale) in views.items():
        render_one(cam, name, loc, target, scale)

    # Neutral clay geometry renders separate silhouette/curvature from EDM materials.
    # This is the authoritative body-fidelity diagnostic.
    ground.hide_render = True
    scene.view_layers[0].material_override = clay
    for name in ('side_driver', 'front', 'front_3q'):
        loc, target, scale = views[name]
        render_one(cam, name + '_clay', loc, target, scale)
    scene.view_layers[0].material_override = None
    ground.hide_render = False

    cam.location = (center.x, -10, 1.15)
    cam.data.ortho_scale = max((length / aspect) * 1.10, 3.45)
    look_at(cam, (center.x, 0, 0.85))
    for frame, name in ((0,'steer_left'), (200,'steer_right')):
        scene.frame_set(frame)
        path = outdir / f'TPG_Tacoma_Recon_QA_{name}.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        if not path.exists() or path.stat().st_size < 10000:
            raise RuntimeError(f'QA steering render missing or too small: {path}')
        print(f'[TPG QA] rendered {path} {path.stat().st_size} bytes')
    scene.frame_set(100)


dump_obj(100, 'TPG_Tacoma_Recon_QA_neutral.obj')
dump_obj(0, 'TPG_Tacoma_Recon_QA_steer_left.obj')
dump_obj(200, 'TPG_Tacoma_Recon_QA_steer_right.obj')
render_views()
bpy.context.scene.frame_set(100)
