import os, runpy
os.environ["TPG_SUB_DESTROYED"] = "0"
os.environ["TPG_SUB_LOD"] = "2"
runpy.run_path("edm-jobs/build_tpg_substation.py", run_name="__main__")
runpy.run_path("edm-jobs/postprocess_tpg_substation_surface_upgrade.py", run_name="__main__")
runpy.run_path("edm-jobs/add_tpg_substation_projector_connectors.py", run_name="__main__")
