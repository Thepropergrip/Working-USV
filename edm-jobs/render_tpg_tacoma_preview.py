import bpy, math, os
from mathutils import Vector
from pathlib import Path

root=Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
out=root/"edm-artifacts"/"TPG_Tacoma_Recon_preview.png"

scene=bpy.context.scene
scene.frame_set(100)
scene.render.engine="BLENDER_WORKBENCH"
scene.render.resolution_x=1600
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=False
scene.display.shading.light="STUDIO"
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.display.shading.cavity_type="WORLD"
scene.display.shading.show_specular_highlight=True
scene.world.color=(0.055,0.055,0.055)

# Ground plane for stance check.
bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,0))
plane=bpy.context.object
plane.name="QA_GROUND"

# Camera at the same front/driver-side three-quarter angle as the user's DCS screenshot.
bpy.ops.object.camera_add(location=(7.2,-6.7,3.3))
cam=bpy.context.object
scene.camera=cam
direction=Vector((0.0,0.0,1.0))-cam.location
cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
cam.data.lens=58

scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
print(f"[TPG QA] preview={out}")
