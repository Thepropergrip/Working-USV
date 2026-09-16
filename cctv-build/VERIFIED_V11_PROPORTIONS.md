# TPG CCTV Pole v1.1 — proportion correction

Status: PACKAGE_VERIFIED / V1.1_DCS_QA_PENDING.

The user confirmed v1.0 renders in DCS but its pole, cameras and cabinet were oversized relative to a person. The user approved reducing component bulk while retaining the 6 m overall height.

## Actual completed build

- Successful native Windows export: run 35163160526, workflow #782.
- Commit: 43969906aeb7c69bc2dbb171f5144b05c0b5c67f.
- Actions artifact: dcs-edm-782, artifact ID 10473289196.
- EDM: TPG_CCTV_Pole.edm, 2,741,192 bytes.
- EDM SHA-256: c483ba68d930f3e343a88d33ebc91d98e05313056cd290c32233a7e1776fb05e.
- Official native ED exporter and Blender 4.1.1 unchanged.

## Geometry

Uses exact vertex ranges for all 61 original source objects, not proximity-based guesses. Each complete camera/mount assembly is scaled uniformly to 40% of v1.0, after measuring the oversized source. Cabinet is 60%. Shaft width is 47%, approximately 173 mm. Base plate is 60%, approximately 513 mm. Cabinet dimensions are approximately 439 H x 367 W x 175 D mm.

Cable cross-section rings are recovered from source connectivity. Diameter is reduced to 35%, endpoints follow the new cabinet/camera connectors, and paths clear the slimmer mast. Correct inverse-transpose/rotation normal transforms are applied. All 31,085 close-view triangles, UVs, material assignments and all six DDS textures are retained. The DDS textures are byte-identical to v1.0.

Upper camera remains at exactly 6 m overall height. Its reduced bracket is re-seated; only the upper shaft segment extends approximately 163 mm to support it. LODs are rebuilt at 31,085 / 9,946 / 2,174 triangles, with a rebuilt 1,398-triangle collision shell.

Build scripts: build_cctv_v11.py and resize_geometry_v11.py. Do not use the abandoned coarse bounding-box grouping script from the conversation. The baseline Git blob is verified using git cat-file because Windows checkout line endings change a raw worktree file hash. The model payload's original strict SHA-256 checks remain intact.

## Delivered package

Conversation attachment: TPG_CCTV_Pole_v1.1_Proportions_Fixed.zip.
Size: 11,042,358 bytes; 20 files; exactly one top-level TPG_CCTV_Pole folder.
ZIP SHA-256: 5711666ae2bf607b10776305bbf897832d9030d324bb741aa8e2072aafa2d021.
This final ZIP is delivered in the conversation, not committed as a binary to this repository.

Replace the existing TPG_CCTV_Pole folder under Saved Games/DCS/Mods/tech. Same plugin/unit/shape identifiers and Structures registration. Do not install both versions side-by-side under alternate folder names.

Passed: native export and artifact digest; EDM hash; unchanged topology/UV/material checks; numerical comparison against local resized mesh; all six texture references and DDS mip/header checks; isolated Lua registration-stub checks; matched-scale before/after and all-LOD visual inspection; ZIP CRC and every file's hash.

No DCS World or ModelViewer test was performed for v1.1. The before/after preview is an exported-mesh render with the actual packaged DDS albedo textures and inspection lighting, not a DCS screenshot. In-game appearance, collision and LOD switching remain runtime checks.
