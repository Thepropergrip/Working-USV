import os, runpy
os.environ["TPG_GAS_DESTROYED"]="0"
runpy.run_path("edm-jobs/build_tpg_gas_station.py", run_name="__main__")
