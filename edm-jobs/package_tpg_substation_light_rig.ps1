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
declare_plugin("TPG Electrical Substation V1.0 LIGHT RIG",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Electrical Substation V1.0 LIGHT RIG"),
    version = "1.0.1",
    state = "installed",
    info = _("Dedicated nine-light illumination rig with explicit EDM bounding and light boxes")
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
TPG Electrical Substation V1.0 LIGHT RIG v1.0.1
================================================

Purpose:
Dedicated lighting asset matched to the exact footprint of TPG Electrical Substation V1.0.

This revision fixes the DCS "Model has invalid bounding box" rejection seen in the prior rig:
- tiny lamp-head meshes now use real Eagle Dynamics EDM materials and export as actual triangles
- a real buried EDM-material anchor mesh exists near origin
- an explicit EDM BOUNDING_BOX spans the entire rig
- an explicit EDM LIGHT_BOX spans the illumination volume
- the nine strong warm-white EDM spot lights are retained

Install:
Copy TPG_Electrical_Substation_V1_LIGHT_RIG into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Substation Light Rig

Placement:
1. Place the normal TPG Electrical Substation V1.0.
2. Place TPG Substation Light Rig at the EXACT SAME coordinates and heading.
3. The tiny rig lamp-head meshes occupy the same fixture locations as the visible substation lights.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
