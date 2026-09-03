import os, runpy
os.environ["TPG_TACOMA_DESTROYED"]="0"
os.environ["TPG_TACOMA_LOD"]="1"
runpy.run_path("edm-jobs/build_tpg_tacoma.py", run_name="__main__")
