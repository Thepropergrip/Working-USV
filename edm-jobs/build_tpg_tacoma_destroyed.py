import os, runpy
runpy.run_path("edm-jobs/prepare_tpg_tacoma_payload.py", run_name="__main__")
os.environ["TPG_TACOMA_DESTROYED"]="1"
os.environ["TPG_TACOMA_LOD"]="0"
runpy.run_path("edm-jobs/build_tpg_tacoma_quality_patch28.py", run_name="__main__")