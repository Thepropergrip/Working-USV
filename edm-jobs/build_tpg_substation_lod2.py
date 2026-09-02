import os, runpy
os.environ["TPG_SUB_DESTROYED"]="0"
os.environ["TPG_SUB_LOD"]="2"
runpy.run_path("edm-jobs/build_tpg_substation.py", run_name="__main__")
