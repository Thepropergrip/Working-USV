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
    version = "1.0.0-LIGHTS",
    state = "installed",
    info = _("High-detail electrical substation static structure with working yard lights")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_electrical_substation_lights.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
local function add_structure(f)
    f.shape_table_data = {
        {
            file = f.ShapeName,
            life = f.Life,
            username = f.Name,
            desrt = f.ShapeNameDestr or "self",
            classname = "lLandVehicle",
            positioning = "BYNORMAL",
        }
    }

    if f.ShapeNameDestr then
        f.shape_table_data[#f.shape_table_data + 1] = {
            name = f.ShapeNameDestr,
            file = f.ShapeNameDestr,
        }
    end

    f.mapclasskey = "P0091000076"
    f.attribute = {wsType_Static, wsType_Standing, "Structures"}
    add_surface_unit(f)
end

add_structure({
    Name = "TPG_Electrical_Substation_V1_LIGHTS",
    DisplayName = _("TPG Electrical Substation V1.0 LIGHTS"),
    ShapeName = "TPG_Electrical_Substation_V1_LIGHTS",
    ShapeNameDestr = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed",
    Life = 1200,
    Rate = 100,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_electrical_substation_lights.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Electrical Substation V1.0 LIGHTS
=====================================

Install:
Copy the folder "TPG_Electrical_Substation_V1_LIGHTS" into:
  Saved Games\DCS\Mods\tech\

This version is intentionally a separate coexisting static asset from:
  TPG_Electrical_Substation_V1

Mission Editor:
Static Objects -> Structures -> TPG Electrical Substation V1.0 LIGHTS

LIGHTS edition:
- Same high-fidelity substation geometry/layout
- Existing nine yard/streetlight fixtures receive real EDM spot-light nodes
- Warm-white localized illumination aimed inward across the yard
- Destroyed model contains no live light sources
- Separate shape/database/plugin names allow both versions to remain installed
- Multiple LODs and dedicated destroyed shape retained
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
