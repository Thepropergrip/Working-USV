import os, runpy
# Assemble and consume the validated FBX-derived Tacoma payload for the intact export.
# Do not route this through the abandoned procedural rebuild/quality-patch stack.
runpy.run_path("edm-jobs/prepare_tpg_tacoma_payload.py", run_name="__main__")
os.environ["TPG_TACOMA_DESTROYED"]="0"
os.environ["TPG_TACOMA_LOD"]="0"
runpy.run_path("edm-jobs/build_tpg_tacoma.py", run_name="__main__")
runpy.run_path("edm-jobs/apply_tpg_tacoma_hero_body_v4.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_hood_equalize_v11.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_wheel_closeout.py", run_name="__main__")