$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Fuel_and_Luuuube_Pro_v110"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Pro_v110.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Pro_v110_Destroyed.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Pro_v110_LOD1.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Pro_v110_LOD2.edm") $shapes -Force

$lods = @'
model={
    lods={
        {"TPG_Fuel_and_Luuuube_Pro_v110.edm",1200.0};
        {"TPG_Fuel_and_Luuuube_Pro_v110_LOD1.edm",3500.0};
        {"TPG_Fuel_and_Luuuube_Pro_v110_LOD2.edm",18000.0};
    };
    collision_shell="TPG_Fuel_and_Luuuube_Pro_v110.edm";
}
'@
Set-Content -Path (Join-Path $shapes "TPG_Fuel_and_Luuuube_Pro_v110.lods") -Value $lods -Encoding ASCII
if (Test-Path (Join-Path $root "Textures")) { Copy-Item (Join-Path $root "Textures\*") $textures -Force }

$entry = @'
declare_plugin("TPG Fuel and Luuuube Pro v1.1.0",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Fuel and Luuuube Pro v1.1.0"),
    version = "1.1.0",
    state = "installed",
    info = _("TPG pro four-dispenser roadside fuel station static structure")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_fuel_pro_v110.lua")
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
    Name = "TPG_Fuel_and_Luuuube_Pro_v110",
    DisplayName = _("TPG Fuel and Luuuube Pro v1.1.0"),
    ShapeName = "TPG_Fuel_and_Luuuube_Pro_v110",
    ShapeNameDestr = "TPG_Fuel_and_Luuuube_Pro_v110_Destroyed",
    Life = 420,
    Rate = 100,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_fuel_pro_v110.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Fuel and Luuuube Pro v1.1.0
================================
Coexistence-safe DCS static structure package.

Install:
Copy the folder "TPG_Fuel_and_Luuuube_Pro_v110" into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Fuel and Luuuube Pro v1.1.0

Coexistence:
This package uses unique plugin, unit, shape, destroyed-shape, LOD, database,
folder, and texture namespaces. It is intended to coexist with earlier
TPG Fuel and Luuuube packages.

Features:
- four physical dispenser cabinets
- double-sided close-range pump detailing
- realistic islands, bollards, hoses, screens, grade buttons and labels
- detailed convenience store with recessed/framed glazing and door hardware
- fake ads/stickers and humorous micro-signage at LOD0
- realistic canopy supports, soffit details and lighting geometry
- HVAC, drains, bins/wiper stands, air/vac, propane area and service clutter
- dual-post framed price pylon with footings and inset price rows
- three visual LOD levels
- dedicated collision geometry
- separate destroyed EDM with structural-collapse damage
- NO scorched/charred building or canopy materials in the destroyed state
- Static Objects -> Structures; not Fortifications
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Fuel_and_Luuuube_Pro_v110_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
