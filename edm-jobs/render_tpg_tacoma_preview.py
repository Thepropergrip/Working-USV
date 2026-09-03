import bpy, os
from pathlib import Path

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

dump_obj(100, "TPG_Tacoma_Recon_QA_neutral.obj")
dump_obj(0, "TPG_Tacoma_Recon_QA_steer_left.obj")
dump_obj(200, "TPG_Tacoma_Recon_QA_steer_right.obj")
bpy.context.scene.frame_set(100)
