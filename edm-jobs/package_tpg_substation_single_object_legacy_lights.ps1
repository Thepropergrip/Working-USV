$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$required = @(
  "TPG_Electrical_Substation_V1.edm",
  "TPG_Electrical_Substation_V1_Destroyed.edm",
  "TPG_Electrical_Substation_V1_LOD1.edm",
  "TPG_Electrical_Substation_V1_LOD2.edm",
  "TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS.edm"
)
foreach ($m in $required) {
  $src = Join-Path $root $m
  if (-not (Test-Path $src)) { throw "Missing required model: $m" }
  Copy-Item $src $shapes -Force
}

# The rendered model remains the known-good high-fidelity substation.
# The collision/auxiliary shell is the legacy EDM v10 LightNode-v1 model that DCS 2.9.29 accepted
# and instantiated as nine live scene lights in the user's test log.
$lods = @'
model={
    lods={
        {"TPG_Electrical_Substation_V1.edm",1500.0};
        {"TPG_Electrical_Substation_V1_LOD1.edm",4500.0};
        {"TPG_Electrical_Substation_V1_LOD2.edm",22000.0};
    };
    collision_shell="TPG_Electrical_Substation_V1_LEGACY_DYNAMIC_LIGHTS.edm";
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
    version = "1.1.0-LEGACY-LIGHT-SHELL",
    state = "installed",
    info = _("High-detail substation with legacy EDM v10 LightNode-v1 auxiliary light shell")
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
    ShapeNameDestr = "TPG_Electrical_Substation_V1_Destroyed",
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

ONE selectable object. No separate overlay placement.

Install:
  Saved Games\DCS\Mods\tech\TPG_Electrical_Substation_V1_LIGHTS

Mission Editor:
  Static Objects -> Structures -> TPG Electrical Substation V1.0 LIGHTS

Architecture:
- Visible render: original high-fidelity substation EDM + its original LODs and textures.
- Auxiliary shell: legacy EDM v10 model::LightNode-v1 file containing nine yard lights.
- No modern SpotLight/OmniLight nodes.
- No GT.lights / lights_data projector controller.
- No visible diagnostic poles.

This package specifically tests whether DCS instantiates the accepted legacy LightNodes while the same object renders the normal substation through its .lods model.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
