$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Fuel_and_Luuuube_Ultra_v120"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Ultra_v120.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Ultra_v120_Destroyed.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Ultra_v120_LOD1.edm") $shapes -Force
Copy-Item (Join-Path $root "TPG_Fuel_and_Luuuube_Ultra_v120_LOD2.edm") $shapes -Force

$lods = @'
model={
    lods={
        {"TPG_Fuel_and_Luuuube_Ultra_v120.edm",1200.0};
        {"TPG_Fuel_and_Luuuube_Ultra_v120_LOD1.edm",3500.0};
        {"TPG_Fuel_and_Luuuube_Ultra_v120_LOD2.edm",18000.0};
    };
    collision_shell="TPG_Fuel_and_Luuuube_Ultra_v120.edm";
}
'@
Set-Content -Path (Join-Path $shapes "TPG_Fuel_and_Luuuube_Ultra_v120.lods") -Value $lods -Encoding ASCII
if (Test-Path (Join-Path $root "Textures")) { Copy-Item (Join-Path $root "Textures\*") $textures -Force }

$entry = @'
declare_plugin("TPG Fuel and Luuuube Ultra v1.2.0",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Fuel and Luuuube Ultra v1.2.0"),
    version = "1.2.0",
    state = "installed",
    info = _("TPG ultra-detail four-dispenser roadside fuel station static structure")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_fuel_ultra_v120.lua")
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
    Name = "TPG_Fuel_and_Luuuube_Ultra_v120",
    DisplayName = _("TPG Fuel and Luuuube Ultra v1.2.0"),
    ShapeName = "TPG_Fuel_and_Luuuube_Ultra_v120",
    ShapeNameDestr = "TPG_Fuel_and_Luuuube_Ultra_v120_Destroyed",
    Life = 420,
    Rate = 100,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_fuel_ultra_v120.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Fuel and Luuuube Ultra v1.2.0
==================================
Coexistence-safe DCS static structure.

Install:
Copy "TPG_Fuel_and_Luuuube_Ultra_v120" into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Fuel and Luuuube Ultra v1.2.0

This is a new package and may remain installed alongside earlier TPG station versions.

v1.2 Ultra highlights:
- four physical high-detail dispenser cabinets
- modeled grade labels 87 / 89 / 93 and selection buttons
- detailed payment bays, keypads, card slots, screens and service seams
- curved hoses plus modeled swivel, breakaway, cradle, nozzle body, trigger guard,
  trigger, metal spout, rubber boot and fittings
- realistic bollard caps, base plates and anchor fasteners
- rebuilt roadside pylon typography, spacing, price rows, dividers and service hardware
- actual layered ad artwork rather than plain text rectangles
- grounded curb-mounted rooftop HVAC units with louvers, condenser fan grilles,
  access-panel screws, disconnect boxes and conduit
- roof vents sit on flashing boots with risers, caps and visible fasteners
- extra roof/parapet/scupper detailing
- destroyed state keeps structural collapse but adds strong fire-blackening,
  soot, char, burned pump internals and ground scorch areas
- LOD1 removes micro-fasteners/text to avoid shimmer; LOD2 preserves station massing
- Structures category, not Fortifications
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Fuel_and_Luuuube_Ultra_v120_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
