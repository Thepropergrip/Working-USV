$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$src = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG.edm"
if (-not (Test-Path $src)) { throw "Missing light rig EDM" }
Copy-Item $src $shapes -Force

if (Test-Path (Join-Path $root "Textures")) {
    Copy-Item (Join-Path $root "Textures\*") $textures -Force
}

$entry = @'
declare_plugin("TPG Electrical Substation V1.0 LIGHT RIG DIAGNOSTIC",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Electrical Substation V1.0 LIGHT RIG DIAGNOSTIC"),
    version = "1.0.2-DIAG",
    state = "installed",
    info = _("Diagnostic nine-light rig with highly visible 8m magenta masts and emissive heads")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_substation_light_rig.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
local function add_structure(f)
    f.shape_table_data = {
        {
            file = f.ShapeName,
            life = 100000,
            username = f.Name,
            classname = "lLandVehicle",
            positioning = "BYNORMAL",
        }
    }
    f.mapclasskey = "P0091000076"
    f.attribute = {wsType_Static, wsType_Standing, "Structures"}
    add_surface_unit(f)
end

add_structure({
    Name = "TPG_Electrical_Substation_V1_LIGHT_RIG",
    DisplayName = _("TPG Substation Light Rig DIAGNOSTIC"),
    ShapeName = "TPG_Electrical_Substation_V1_LIGHT_RIG",
    Life = 100000,
    Rate = 1,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_substation_light_rig.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Electrical Substation V1.0 LIGHT RIG DIAGNOSTIC v1.0.2
============================================================

This is a deliberately obvious diagnostic build.

Daylight proof-of-load geometry:
- nine full-height ~8 m fluorescent-magenta masts
- large orange base plates
- oversized warm-white emissive lamp heads
- visible crossbars

Lighting:
- same nine real EDM spot lights, strengthened for the test
- explicit EDM BOUNDING_BOX and LIGHT_BOX retained

Purpose:
If the magenta masts appear in Mission Editor/in-game, DCS is definitely instantiating the asset.
If the masts appear but no terrain illumination appears at night, the remaining problem is specifically
runtime servicing of the EDM light nodes rather than model loading/bounds/materials.

Install:
REPLACE the prior TPG_Electrical_Substation_V1_LIGHT_RIG folder in:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Substation Light Rig DIAGNOSTIC

Placement:
Place at the exact same coordinates and heading as TPG Electrical Substation V1.0.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
