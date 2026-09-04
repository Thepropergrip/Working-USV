$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG"
$shapes = Join-Path $pkg "Shapes"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$db | Out-Null

$src = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG.edm"
if (-not (Test-Path $src)) { throw "Missing light rig EDM" }
Copy-Item $src $shapes -Force

$entry = @'
declare_plugin("TPG Electrical Substation V1.0 LIGHT RIG",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Electrical Substation V1.0 LIGHT RIG"),
    version = "1.0.0",
    state = "installed",
    info = _("Dedicated nine-light illumination rig matched to the TPG Electrical Substation V1.0 footprint")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
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
    DisplayName = _("TPG Substation Light Rig"),
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
TPG Electrical Substation V1.0 LIGHT RIG
=========================================

Purpose:
Dedicated light-only asset matched to the exact footprint of TPG Electrical Substation V1.0.
This follows the proven DCS pattern used by dedicated airfield/flood-light effect assets: the light
source is its own object instead of being embedded inside the visible structure.

Install:
Copy TPG_Electrical_Substation_V1_LIGHT_RIG into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Substation Light Rig

Placement:
1. Place the normal TPG Electrical Substation V1.0.
2. Place TPG Substation Light Rig at the EXACT SAME coordinates and heading.
3. The rig geometry is intentionally buried/invisible; only its nine EDM spot lights should be visible at night.

The rig uses nine strong warm-white spot lights aligned to the substation yard light positions.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
