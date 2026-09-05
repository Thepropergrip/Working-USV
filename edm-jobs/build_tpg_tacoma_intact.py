import os, runpy
# Canonical FBX-derived Tacoma intact export. No patch-on-patch body chain.
runpy.run_path("edm-jobs/prepare_tpg_tacoma_payload.py", run_name="__main__")
os.environ["TPG_TACOMA_DESTROYED"]="0"
os.environ["TPG_TACOMA_LOD"]="0"
runpy.run_path("edm-jobs/build_tpg_tacoma.py", run_name="__main__")
runpy.run_path("edm-jobs/diagnose_tpg_tacoma_source_mesh.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_clean_rebuild_v13.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_wheel_closeout.py", run_name="__main__")
