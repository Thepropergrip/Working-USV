# TPG CCTV Pole — verified build checkpoint

Date: 2026-09-16. Status: **PACKAGE_VERIFIED / DCS_QA_PENDING**.

## Successful native export
- Workflow run #780: https://github.com/Thepropergrip/Working-USV/actions/runs/35159721335
- Source commit: `7b2758cd4c56c8c77ab8331f419373570773ba7c`.
- Artifact: `dcs-edm-780`, artifact ID `10472471805`.
- Native `TPG_CCTV_Pole.edm`: **2,743,484 bytes**.
- EDM SHA-256: `16945f6873f518df43d06d66ac69352cc935a1dc01bc9260f2ee843dd73158ee`.
- Windows, Blender 4.1.1, official ED exporter pinned to `5f03ba70ec96ca6ce68028eabc786ecd97f9cf93`, genuine native bindings.

## Source repair — do not repeat the old truncation
The actual staged encoding is 252640 base64 characters, NOT 252560. Shard 015 contains 12640 valid characters. Shard 006 has one extra trailing Y; remove it ONLY after verifying its exact original SHA. The verified build script performs hard checksum assertions before decoding. Do not use the previous permissive build_cctv_complete.py.

Verified base64 SHA-256: `30c08205f78f2d96f6920a09e425ea1c99ad0bd875c5738b7abd952fcf4f3a3a`.
Decoded bytes: 532843. Decoded SHA-256: `76c92b5e552935fb12dbebffb6a744da803c521ad377ed2fa17ba2bfa0aca724`.
Compared against the original OBJ extracted from CCTV.rar: all triangle, UV-corner, normal-corner and material assignments match; position quantization error is below 0.046 mm at final scale.

## Mod packaging
Final delivered conversation attachment: `TPG_CCTV_Pole_v1.0.zip`, **11,044,201 bytes**, SHA-256 `feeb3eed3611d22797cd3ae3eadcfcacf6f8c9bb4cad814f22f87c289b376985`.
Exactly one top-level `TPG_CCTV_Pole` folder; 21 files. This final ZIP is not stored in this Git repository. The native export remains in the Actions artifact above.

The mod directory here contains the actual registration source and credits, NOT the complete installable mod. Packaging requires the genuine native EDM and all SIX original-source-derived 2048px DDS textures. The export artifact's tiny PNG images are REFERENCE PLACEHOLDERS ONLY: never put them in the final mod.

Texture filenames must be lower-case to exactly match EDM bindings: `tpg_cctv_map_{one,two}_{basecolor,normal,roughmet}.dds`. DDS format BC3/DXT5, 12 mip levels, 5592560 bytes each. RoughMet R=source AO, G=source roughness, B=source metallic. Original camera markings and texture layout retained.

Height 6 m, uniform scaling. LOD triangle counts: 31085 / 9946 / 2174. Native internal LOD distance settings: 300 / 1000 / 6000 m. Separate collision shell: 1398 triangles. Mounting-plate-centered origin, ground minimum zero, upright ONLYHEIGTH placement.

Validation passed: native export integrity and SHA; six exact texture references; DDS headers/mips; Lua parse and strict registration stub; ZIP CRC and extraction hashes; six matched source/export mesh viewpoints (silhouette IoU 1.0 in every test); visual inspection of textured LODs.

DCS World and ModelViewer were NOT run. The previews are exported Blender mesh QA with final albedo textures, not DCS screenshots or full shader/runtime validation. Runtime collision, LOD switches and Mission Editor placement remain to be checked in DCS.
