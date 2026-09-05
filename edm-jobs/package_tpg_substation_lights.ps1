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
    version = "1.2.0-MASSUN-DONOR",
    state = "installed",
    info = _("High-detail electrical substation with nine donor-matched legacy LightNode v1 floodlights embedded directly in the rendered EDM")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_electrical_substation_lights.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
-- LIGHTS v1.2 uses the exact architecture proven by the user-provided working
-- Massun92 watchtower EDM: legacy model::LightNode v1 SPOT nodes embedded directly
-- in the rendered EDM. No GT.lights / lights_data controller is used.

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
TPG Electrical Substation V1.0 LIGHTS v1.2.0 MASSUN DONOR
==========================================================

INSTALL
Delete/replace any older folder named:
  TPG_Electrical_Substation_V1_LIGHTS

Then copy this folder into:
  Saved Games\DCS\Mods\tech\

The untouched original remains compatible and can coexist:
  TPG_Electrical_Substation_V1

MISSION EDITOR
Static Objects -> Structures -> TPG Electrical Substation V1.0 LIGHTS

WHAT IS DIFFERENT
This build is based directly on the user-provided known-working in-game Massun92
M92_Container_watchtower_lights EDMs, not on guessed Lua projector definitions.

Binary inspection of the working donor showed its main floods are:
- EDM v10 model::LightNode
- LightNode __VERSION__ = 1
- isSpot = 1
- Color = {1.0, 0.9, 0.9}
- Brightness = 0.07
- Phi = 1.0
- Theta = 0.5
- Distance = 500.0

The intact substation and LOD1/LOD2 are first exported by the official ED exporter
with nine correctly aimed transform/connectors and emissive fixture lenses. A binary
post-process then injects nine legacy LightNode v1 records using the exact donor values
and parents each one to the corresponding fixture transform.

There are:
- NO modern official-exporter SpotLight/OmniLight nodes
- NO GT.lights
- NO GT.lights_data
- NO secondary overlay object
- NO light EDM hidden in the collision shell

The far/destroyed models intentionally carry no active donor lights, matching the donor
principle of omitting light nodes from the farthest LOD.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
