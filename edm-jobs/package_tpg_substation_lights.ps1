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
    version = "1.3.1-CRASHFIX-STATIC055",
    state = "installed",
    info = _("High-detail substation with inward legacy LightNode v1 floods, deeper terrain bed, and tiled PBR surfaces; animated light gating removed after confirmed DCS preview crash")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_electrical_substation_lights.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
-- TPG Electrical Substation LIGHTS v1.3.1 CRASHFIX
-- Static legacy LightNode v1 floods: brightness 0.55, range 160 m.
-- Animated Brightness / headlight-argument gating was removed after a confirmed
-- ModelDesc.dll model::LightNode::apply access violation in DCS 2.9.29.27468.

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
TPG Electrical Substation V1.0 LIGHTS v1.3.1 CRASHFIX
======================================================

INSTALL
Delete/replace any older folder named:
  TPG_Electrical_Substation_V1_LIGHTS

Copy this folder into:
  Saved Games\DCS\Mods\tech\

MISSION EDITOR
Static Objects -> Structures -> TPG Electrical Substation V1.0 LIGHTS

PRESERVED
- Proven Massun-style legacy model::LightNode v1 architecture.
- Nine flood transforms aimed inward/down into the facility.
- Brightness 0.55 and effective distance 160 m.
- Non-emissive daytime lens material.
- Deeper buried foundation skirt for uneven terrain.
- Meter-scaled/tiled ground-bed and control-building UV treatment.
- Dedicated normal-map slots for supplied ground_0020 and bricks_0015 PBR sets.
- Destroyed model remains dark.

CRASH FIX
The previous v1.3.0 experiment animated LightNode Brightness directly on DCS headlight
argument 31. Selecting the asset in the Mission Editor produced a confirmed
ModelDesc.dll model::LightNode::apply access violation. That AnimatedProperty encoding
has been removed and the donor-compatible static Property<float> Brightness restored.

The lights therefore remain static in this safe build. Automatic day/night control must
be implemented by a different mechanism rather than animating legacy LightNode Brightness.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
