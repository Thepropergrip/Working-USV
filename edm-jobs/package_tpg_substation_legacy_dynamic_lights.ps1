$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS"
$shapes = Join-Path $pkg "Shapes"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$db | Out-Null

$src = Join-Path $root "TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS.edm"
if (-not (Test-Path $src)) { throw "Missing legacy dynamic light EDM" }
Copy-Item $src $shapes -Force

$entry = @'
declare_plugin("TPG Electrical Substation V1.0 LEGACY DYNAMIC LIGHTS",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Electrical Substation V1.0 LEGACY DYNAMIC LIGHTS"),
    version = "1.0.0-LEGACY-LIGHTNODE-V1",
    state = "installed",
    info = _("Light-only overlay using legacy EDM v10 model::LightNode v1 dynamic lights; no Lua GT light controller")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
dofile(current_mod_path.."/Database/db_tpg_substation_legacy_dynamic_lights.lua")
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
    Name = "TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS",
    DisplayName = _("TPG Substation LEGACY DYNAMIC LIGHTS"),
    ShapeName = "TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS",
    Life = 100000,
    Rate = 1,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_substation_legacy_dynamic_lights.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Electrical Substation V1.0 LEGACY DYNAMIC LIGHTS
=====================================================

PURPOSE
This is a light-only overlay for the normal high-fidelity TPG Electrical Substation V1.0.
It contains nine legacy EDM v10 model::LightNode v1 dynamic omni lights.
It intentionally contains:
- NO modern official-exporter SpotLight/OmniLight nodes
- NO GT.lights or GT.lights_data controller
- NO visible diagnostic poles

WHY
DCS 2.9.29 rejected the modern Blender light encoding with "Wrong light version".
The legacy Blender exporter writes the older LightNode v1 encoding used by the generation of
known-working dedicated DCS light-effect assets.

INSTALL
Copy folder into:
  Saved Games\DCS\Mods\tech\TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS

MISSION EDITOR
Static Objects -> Structures -> TPG Substation LEGACY DYNAMIC LIGHTS

PLACEMENT
Place this object at EXACTLY the same coordinates and heading as:
  TPG Electrical Substation V1.0

The overlay has no pole geometry. The nine dynamic light sources are positioned at the
substation's yard-light height/locations and should illuminate terrain, station hardware,
and nearby vehicles at night if DCS accepts the legacy LightNode v1 path.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
