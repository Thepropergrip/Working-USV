import os, runpy
runpy.run_path("edm-jobs/prepare_tpg_tacoma_payload.py", run_name="__main__")
os.environ["TPG_TACOMA_DESTROYED"]="0"
os.environ["TPG_TACOMA_LOD"]="1"
runpy.run_path("edm-jobs/build_tpg_tacoma_quality_patch24.py", run_name="__main__")