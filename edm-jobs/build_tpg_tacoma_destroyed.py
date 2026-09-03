import os, runpy
os.environ["TPG_TACOMA_DESTROYED"]="1"
os.environ["TPG_TACOMA_LOD"]="0"
runpy.run_path("edm-jobs/build_tpg_tacoma.py", run_name="__main__")
