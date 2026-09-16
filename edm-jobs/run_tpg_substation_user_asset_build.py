from pathlib import Path

# Execute the normal substation builder, but install user-asset visual overrides
# immediately before the scene-construction call sequence. This keeps the original
# builder layout/placement intact while replacing only the requested visual systems.

path = Path("edm-jobs/build_tpg_substation.py")
source = path.read_text(encoding="utf-8")
needle = "base()\nfence()\ncontrol_building()\ntransformer(-23,10,1,DESTROYED)"
insert = (
    "from tpg_substation_user_asset_upgrade import apply_prebuild_overrides\n"
    "apply_prebuild_overrides(globals())\n\n"
    "base()\nfence()\ncontrol_building()\ntransformer(-23,10,1,DESTROYED)"
)
if needle not in source:
    raise RuntimeError("Could not locate substation scene-build call sequence for user asset override injection")
source = source.replace(needle, insert, 1)
exec(compile(source, str(path), "exec"), globals(), globals())
