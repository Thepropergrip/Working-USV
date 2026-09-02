$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Fuel_and_Luuuube"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Destroyed.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_LOD1.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_LOD2.edm") $shapes -Force

$lods = @'
model={
    lods={
        {"TPG_Fuel_and_Luuuube.edm",1200.0};
        {"TPG_Fuel_and_Luuuube_LOD1.edm",3500.0};
        {"TPG_Fuel_and_Luuuube_LOD2.edm",18000.0};
    };
    collision_shell="TPG_Fuel_and_Luuuube.edm";
}
'@
Set-Content -Path (Join-Path $shapes "TPG_Fuel_and_Luuuube.lods") -Value $lods -Encoding ASCII
if (Test-Path (Join-Path $root "Textures")) { Copy-Item (Join-Path $root "Textures\*") $textures -Force }

$entry = @'
declare_plugin("TPG Fuel and Luuuube",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Fuel and Luuuube"),
    version = "1.1.0",
    state = "installed",
    info = _("TPG four-position roadside fuel station static structure")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_fuel.lua")
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
    Name = "TPG_Fuel_and_Luuuube",
    DisplayName = _("TPG Fuel and Luuuube"),
    ShapeName = "TPG_Fuel_and_Luuuube",
    ShapeNameDestr = "TPG_Fuel_and_Luuuube_Destroyed",
    Life = 420,
    Rate = 100,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_fuel.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Fuel and Luuuube v1.1.0
================================
DCS static structure.

Install:
Copy the folder "TPG_Fuel_and_Luuuube" into:
  Saved Games\DCS\Mods\tech\
(or Saved Games\DCS.openbeta\Mods\tech\ if your install still uses that folder name)

Mission Editor:
Static Objects -> Structures -> TPG Fuel and Luuuube

Features:
- 2 pump islands
- 1 double-sided dispenser on each island
- 4 total fueling positions
- TPG Fuel and Luuuube branding
- Regular 87 price starts at $3.95/gal
- detailed convenience store, framed/recessed glazing, door hardware, stickers and fake ads\n- realistic canopy structure, soffit seams/lights, HVAC, drains, bins/wiper stands, air/vac and propane area\n- dual-post framed price pylon with footings, service panel, fasteners and inset grade/price rows
- dedicated collision shells
- three visual LOD levels (LOD0 / LOD1 / LOD2)
- separate destroyed EDM using structural-collapse damage only; building/canopy materials are intentionally NOT scorched or charred
- textured PBR materials generated for DCS EDM export\n- humorous micro-signage at LOD0, removed from distance LODs to prevent shimmer
- static structure registration; not Fortifications
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Fuel_and_Luuuube_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
