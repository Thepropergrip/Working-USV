import os, runpy
# Canonical FBX-derived Tacoma intact export. No patch-on-patch body chain.
runpy.run_path("edm-jobs/prepare_tpg_tacoma_payload.py", run_name="__main__")
os.environ["TPG_TACOMA_DESTROYED"]="0"
os.environ["TPG_TACOMA_LOD"]="0"
runpy.run_path("edm-jobs/build_tpg_tacoma.py", run_name="__main__")
runpy.run_path("edm-jobs/diagnose_tpg_tacoma_source_mesh.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_clean_rebuild_v13.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_photo_match_v14.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_cab_topper_match_v15.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_cab_front_profile_v16.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_glasshouse_beltline_v17.py", run_name="__main__")
runpy.run_path("edm-jobs/build_tpg_tacoma_wheel_closeout.py", run_name="__main__")
