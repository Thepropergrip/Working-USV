import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
OUT = ROOT / "hires-generated" / "preview-v5"
OUT.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.display.shading.curvature_ridge_factor = 1.4
scene.display.shading.curvature_valley_factor = 1.2
scene.render.film_transparent = False

# Hide non-visual helpers/connectors from QA renders.
for obj in bpy.data.objects:
    if obj.type in {"EMPTY", "LIGHT"}:
        obj.hide_render = True

# Create dedicated QA camera.
cam_data = bpy.data.cameras.new("HiResV5_QA_Camera_Data")
cam = bpy.data.objects.new("HiResV5_QA_Camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.lens = 52


def aim_camera(location, target):
    cam.location = Vector(location)
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()

views = [
    ("front_starboard", (6.5, -7.2, 3.7), (0.3, 0.0, 1.45)),
    ("aft_starboard", (-5.8, -7.0, 3.1), (-0.4, 0.0, 1.45)),
    ("starboard_close", (1.8, -6.2, 2.25), (0.0, 0.0, 1.65)),
    ("top_oblique", (5.0, -6.5, 7.0), (0.0, 0.0, 1.25)),
]

for name, loc, target in views:
    aim_camera(loc, target)
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"MAGURA_V5_PREVIEW={scene.render.filepath}")

# Remove only the temporary render camera so it cannot enter the EDM export.
bpy.data.objects.remove(cam, do_unlink=True)
bpy.data.cameras.remove(cam_data, do_unlink=True)
print("MAGURA_HIRES_V5_PREVIEWS_READY=1")
