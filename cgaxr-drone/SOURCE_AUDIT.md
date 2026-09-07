# CGAXR MC Drone source audit

This DCS conversion was built from the complete source set supplied by the user. The OBJ is the authoritative dense mesh/UV topology, while FBX/Maya/V-Ray files were used to cross-check geometry, object naming, orientation, and authored shader intent. The supplied lens image was extracted from `Texture.rar` and applied to the source UV-mapped front-camera geometry.

## Source fingerprints

| Source | SHA-256 | Use |
|---|---|---|
| `CGAXR_MC_Drone_OBJ.obj` | `7ee78ca9d0c517beea2358dbacac31bfd41db984d90b726c957dc5df44a89a5a` | Authoritative mesh, groups, faces and UV topology |
| `CGAXR_MC_Drone_OBJ.mtl` | `a587e92da8b99e158446052c74b9944c6e36689e96404a6031c58aee095fdea4` | Material assignment cross-check |
| `CGAXR_MC_Drone_FBX.fbx` | `425084df886134c290b20372fefe7e9a97420ff348d308732991e957cb577b81` | Source-model/geometry cross-check |
| `CGAXR_MC_Drone_MA(2).ma` | `f99741bbd99ee86a0898c0d13f38cd7a414510892caf9251dbc8684ff311d5da` | Maya material/object-network cross-check |
| `CGAXR_MC_Drone_MB.mb` | `936ba67890b23f591c108bce5aa921ce065d014ec1481dc9974334142e9d6073` | Binary Maya source cross-check |
| `CGAXR_MC_Drone_Vray(1).vrscene` | `2a41a369f16986068dd15401217a0e647960c297bc4ee514ca8290746d478544` | Authoritative V-Ray shader values and object/material mapping |
| `Texture.rar` | `a46727d4f10d620126a68ebb56bb6a69e68fb53b00522739f73bd0ba992e2ee6` | Original supplied texture archive |
| `AXR_Lense_01.jpg` | `b8dc21160561ca2781ed2f547de3ed890c528905d94e16f14578fad1018deedc` | Original camera-lens texture |

## Geometry preservation

- 688,564 referenced source vertices
- 677,964 polygons (676,734 quads + 1,230 triangles), none decimated
- 54,776 referenced UV vertices, preserving all source UV-mapped faces
- Source units are centimeters; converted to meters
- Maya/source +Z is the model nose/front, mapped to DCS +X; source +Y maps to DCS/Blender +Z (up)
- Position payload uses 13-bit bbox quantization only to transport the model through GitHub text APIs. Maximum coordinate step is ~0.132 mm across the ~1.08 m rotor span; no polygon or component is removed.

## V-Ray -> DCS PBR translation

The source package is primarily shader-driven rather than dependent on a missing texture library. DCS PBR materials reproduce these source values as closely as the EDM material system permits:

- `CGAXR_MC_Plastic`: black, reflection glossiness 0.7 -> DCS roughness ~0.30
- `CGAXR_MC_Glass_ref`: clear reflective glass, IOR 1.6, pale green fog tint -> ED glass material
- `CGAXR_MC_Frosted_Glass`: refraction 0.76034 / glossiness 0.85 -> translucent frosted ED glass
- `CGAXR_MC_Aluminium`: diffuse `(0.702, 0.6892037, 0.661284)`, reflection glossiness `0.493421`
- `CGAXR_MC_Rim`: Fresnel base `(0.2457, 0.2548, 0.273)`, reflection glossiness `0.5`
- `CGAXR_MC_color_shadder`: falloff colors `(0.541,0.4549791,0.225597)` / `(0.493,0.3705203,0.101065)`, flake colors `(0.5960785,0.5215687,0.3607843)` / `(0.4470588,0.3843137,0.2156863)`, reflection glossiness `0.6381579`

The supplied lens texture corresponds to the only source front-camera geometry carrying a full 0-1 UV layout (`CGAXR_MC_Drone_Camera14`); its separate `Camera5` mesh remains the clear glass cover.
