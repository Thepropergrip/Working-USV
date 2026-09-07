$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$unitName = "TPG_Gas_Station_V1_2_Liveries"
$pkg = Join-Path $root $unitName
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
$liveriesRoot = Join-Path $pkg ("Liveries\" + $unitName)
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db,$liveriesRoot | Out-Null

Copy-Item (Join-Path $root ($unitName + ".edm")) $shapes -Force
Copy-Item (Join-Path $root ($unitName + "_Destroyed.edm")) $shapes -Force
Copy-Item (Join-Path $root ($unitName + "_LOD1.edm")) $shapes -Force
Copy-Item (Join-Path $root ($unitName + "_LOD2.edm")) $shapes -Force
Copy-Item (Join-Path $root ($unitName + "_Collision.edm")) $shapes -Force

$lods = @'
model={
    lods={
        {"TPG_Gas_Station_V1_2_Liveries.edm",1200.0};
        {"TPG_Gas_Station_V1_2_Liveries_LOD1.edm",3500.0};
        {"TPG_Gas_Station_V1_2_Liveries_LOD2.edm",18000.0};
    };
    collision_shell="TPG_Gas_Station_V1_2_Liveries_Collision.edm";
}
'@
Set-Content -Path (Join-Path $shapes ($unitName + ".lods")) -Value $lods -Encoding ASCII

if (Test-Path (Join-Path $root "Textures")) {
    Copy-Item (Join-Path $root "Textures\*") $textures -Force
}

$liverySource = Join-Path $root "LiveryTextures"
Copy-Item (Join-Path $liverySource "USA\*.png") $textures -Force

$keys = @(
    "PYLON","PRICELED","STORE_SIGN","CANOPY_SIGN","PUMP_SCREEN","PAY","NOSMOKE",
    "GRADE1","GRADE2","GRADE3","DOOR_HOURS","DOOR_PUSH","AIRVAC","PROPANE",
    "ATM","ICE","NEWS","FIRE","AFRAME","AD_TACO","AD_COFFEE","AD_LOTTO","AD_WIPER"
)

foreach ($variant in @("USA","Russia","Syria")) {
    $dst = Join-Path $liveriesRoot $variant
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    Copy-Item (Join-Path $liverySource ($variant + "\*.png")) $dst -Force

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("livery = {")
    foreach ($key in $keys) {
        $mat = "TPG_GS_L10N_" + $key
        $tex = "TPG_GS_L10N_" + $key + "_" + $variant
        $lines.Add(('    {"' + $mat + '", 0, "' + $tex + '", false},'))
        if ($key -eq "PRICELED") {
            $lines.Add(('    {"' + $mat + '", 8, "' + $tex + '", false},'))
        }
    }
    $lines.Add("}")
    $lines.Add(('name = "' + $variant + '"'))
    Set-Content -Path (Join-Path $dst "description.lua") -Value $lines -Encoding UTF8
}

$entry = @'
declare_plugin("TPG Gas Station V1.2 Livery Edition",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Gas Station V1.2 Livery Edition"),
    version = "1.2.0",
    state = "installed",
    info = _("Four-dispenser roadside gas station with USA, Russia and Syria liveries")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
mount_vfs_liveries_path(current_mod_path.."/Liveries")
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
    Name = "TPG_Gas_Station_V1_2_Liveries",
    DisplayName = _("TPG Gas Station V1.2 Livery Edition"),
    ShapeName = "TPG_Gas_Station_V1_2_Liveries",
    ShapeNameDestr = "TPG_Gas_Station_V1_2_Liveries_Destroyed",
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
TPG Gas Station V1.2 - Livery Edition
======================================

Install:
Copy the single folder "TPG_Gas_Station_V1_2_Liveries" directly into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Gas Station V1.2 Livery Edition

Liveries:
- USA: English signage; Regular 87 / Plus 89 / Premium 93; USD per gallon.
- Russia: Russian signage; AI-92 / AI-95 / AI-100; rubles per liter.
- Syria: Arabic signage; 90 / 95 / 98 grades; Syrian pounds per liter.

The physical station is identical between liveries. Only localized language,
pricing and units of measurement change. USA is the default/base appearance.

Retained from V1.1:
- Four detailed fuel dispensers
- Convenience store and canopy
- Illuminated/emissive roadside price display
- Rooftop HVAC and vent details
- Vehicle-friendly collision geometry
- Corrected raised asphalt forecourt (z-fighting fix)
- Distance LODs
- Separate destroyed model

This V1.2 uses a unique DCS namespace and can coexist with V1.1.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Gas_Station_V1.2_Livery_Edition_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
