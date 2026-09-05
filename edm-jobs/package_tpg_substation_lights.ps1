$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$models = @(
  "TPG_Electrical_Substation_V1_LIGHTS.edm",
  "TPG_Electrical_Substation_V1_LIGHTS_Destroyed.edm",
  "TPG_Electrical_Substation_V1_LIGHTS_LOD1.edm",
  "TPG_Electrical_Substation_V1_LIGHTS_LOD2.edm"
)
foreach ($m in $models) {
  $src = Join-Path $root $m
  if (-not (Test-Path $src)) { throw "Missing required model: $m" }
  Copy-Item $src $shapes -Force
}

$lods = @'
model={
    lods={
        {"TPG_Electrical_Substation_V1_LIGHTS.edm",1500.0};
        {"TPG_Electrical_Substation_V1_LIGHTS_LOD1.edm",4500.0};
        {"TPG_Electrical_Substation_V1_LIGHTS_LOD2.edm",22000.0};
    };
    collision_shell="TPG_Electrical_Substation_V1_LIGHTS.edm";
}
'@
Set-Content -Path (Join-Path $shapes "TPG_Electrical_Substation_V1_LIGHTS.lods") -Value $lods -Encoding ASCII

if (Test-Path (Join-Path $root "Textures")) {
    Copy-Item (Join-Path $root "Textures\*") $textures -Force
}

$entry = @'
declare_plugin("TPG Electrical Substation V1.0 LIGHTS",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Electrical Substation V1.0 LIGHTS"),
    version = "1.3.0-NIGHT-GATED-TEXTURED",
    state = "installed",
    info = _("High-detail substation with inward legacy LightNode floods, automatic night gating, deeper terrain bed, and tiled PBR surface upgrade")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_electrical_substation_lights.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
-- LIGHTS v1.3
-- Embedded legacy LightNode v1 floods are brightness-animated on argument 31.
-- Registering as a stationary ground unit and declaring headlights=31 lets DCS
-- drive the lights off in daylight and on when ground-unit headlights are active.

GT = {}
GT_t.ws = 0
set_recursive_metatable(GT, GT_t.generic_stationary)
set_recursive_metatable(GT.chassis, GT_t.CH_t.STATIC)

GT.chassis.life = 1200
GT.visual.shape = "TPG_Electrical_Substation_V1_LIGHTS"
GT.visual.shape_dstr = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed"
GT.visual.fire_size = 0.8
GT.visual.fire_pos = {0, 0, 0}
GT.visual.fire_time = 120
GT.time_agony = 180

GT.Name = "TPG_Electrical_Substation_V1_LIGHTS"
GT.DisplayName = _("TPG Electrical Substation V1.0 LIGHTS")
GT.Rate = 100
GT.DetectionRange = 0
GT.ThreatRange = 0
GT.mapclasskey = "P0091000076"
GT.positioning = "BYNORMAL"
GT.CustomAimPoint = {0, 4.0, 0}

GT.animation_arguments = {
    headlights = 31,
}

GT.attribute = {
    wsType_Ground,
    wsType_Tank,
    wsType_NoWeapon,
    wsType_GenericFort,
    "Fortifications",
}
GT.category = "Fortification"

GT.shape_table_data = {
    {
        file = "TPG_Electrical_Substation_V1_LIGHTS",
        life = 1200,
        username = "TPG_Electrical_Substation_V1_LIGHTS",
        desrt = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed",
        classname = "lLandVehicle",
        positioning = "BYNORMAL",
    },
    {
        name = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed",
        file = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed",
    }
}

add_surface_unit(GT)
GT = nil
'@
Set-Content -Path (Join-Path $db "db_tpg_electrical_substation_lights.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Electrical Substation V1.0 LIGHTS v1.3.0
================================================

INSTALL
Delete/replace any older folder named:
  TPG_Electrical_Substation_V1_LIGHTS

Copy this folder into:
  Saved Games\DCS\Mods\tech\

The untouched original can coexist:
  TPG_Electrical_Substation_V1

MISSION EDITOR
Ground Units -> Fortification -> TPG Electrical Substation V1.0 LIGHTS

CHANGES IN THIS BUILD
- Proven Massun-style legacy model::LightNode v1 architecture retained.
- Nine flood transforms are corrected to face inward/down into the facility.
- Flood maximum brightness reduced to 0.55 from the overexposed 5.0 test.
- Effective light distance reduced to 160 m from 500 m to stop washing out surrounding terrain.
- Light brightness is animated on DCS ground-unit headlights argument 31:
  daytime/off = 0, nighttime/on = 0.55.
- Permanent emissive lamp-lens glow removed so fixtures do not appear lit during the day.
- Foundation buried skirt deepened to about 1.65 m below local origin to hide exposed flat edges on uneven terrain.
- Ground-bed UVs use meter-scaled planar projection around slopes/bends instead of one stretched wrap.
- Main control-building brick UVs use meter-scaled projection around sides/bevels.
- Ground and brick materials contain dedicated normal-map slots for the supplied PBR texture sets.
- Destroyed model remains dark.

The final distributed package replaces the generated ground and brick texture placeholders
with the user's supplied ground_0020 and bricks_0015 color/normal/AO/roughness maps.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"