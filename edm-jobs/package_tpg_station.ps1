$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Gas_Station_V1"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

Copy-Item (Join-Path $root "TPG_Gas_Station_V1.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Gas_Station_V1_Destroyed.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Gas_Station_V1_LOD1.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Gas_Station_V1_LOD2.edm") $shapes -Force

$lods = @'
model={
    lods={
        {"TPG_Gas_Station_V1.edm",1200.0};
        {"TPG_Gas_Station_V1_LOD1.edm",3500.0};
        {"TPG_Gas_Station_V1_LOD2.edm",18000.0};
    };
    collision_shell="TPG_Gas_Station_V1.edm";
}
'@
Set-Content -Path (Join-Path $shapes "TPG_Gas_Station_V1.lods") -Value $lods -Encoding ASCII

if (Test-Path (Join-Path $root "Textures")) {
    Copy-Item (Join-Path $root "Textures\*") $textures -Force
}

$entry = @'
declare_plugin("TPG Gas Station V1.0",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Gas Station V1.0"),
    version = "1.0.0",
    state = "installed",
    info = _("Four-dispenser roadside gas station static structure")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_gas_station.lua")
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
    Name = "TPG_Gas_Station_V1",
    DisplayName = _("TPG Gas Station V1.0"),
    ShapeName = "TPG_Gas_Station_V1",
    ShapeNameDestr = "TPG_Gas_Station_V1_Destroyed",
    Life = 420,
    Rate = 100,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_gas_station.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Gas Station V1.0
====================

Install:
Copy the folder "TPG_Gas_Station_V1" into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Gas Station V1.0

Contents:
- Four detailed fuel dispensers
- Convenience store and canopy
- Roadside price sign
- Rooftop HVAC and vent details
- Collision geometry
- Distance LODs
- Separate destroyed model
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Gas_Station_V1.0_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
