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
    version = "1.1.0-PROJECTOR",
    state = "installed",
    info = _("High-detail electrical substation with nine connector-driven DCS projector floods and emissive fixture lenses")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_electrical_substation_lights.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
-- TPG Electrical Substation V1.0 LIGHTS v1.1.0
--
-- IMPORTANT CHANGE FROM THE FAILED TESTS:
--  * The visible substation EDM itself now contains nine correctly oriented EDM connectors.
--  * There are ZERO embedded Blender/official-exporter Light nodes (avoids Wrong light version).
--  * The fixture lenses are real emissive EDM material geometry.
--  * DCS projector lights use the current "Spot" + lamp_prototypes form WITHOUT the
--    intensity_max=20/24 override that made the previous projector tests effectively marker lights.
--  * A low-power omni fill is paired with each projector to provide local ambient spill.

GT = {}
GT_t.ws = 0
set_recursive_metatable(GT, GT_t.generic_stationary)
set_recursive_metatable(GT.chassis, GT_t.CH_t.STATIC)

GT.chassis.life = 1200
GT.visual.shape = "TPG_Electrical_Substation_V1_LIGHTS"
GT.visual.shape_dstr = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed"
GT.visual.fire_size = 0.8
GT.visual.fire_pos = {0, 0, 0}
GT.visual.fire_time = 120
GT.time_agony = 180

GT.Name = "TPG_Electrical_Substation_V1_LIGHTS"
GT.DisplayName = _("TPG Electrical Substation V1.0 LIGHTS")
GT.Rate = 100
GT.DetectionRange = 0
GT.ThreatRange = 0
GT.mapclasskey = "P0091000076"
GT.positioning = "BYNORMAL"
GT.CustomAimPoint = {0, 4.0, 0}

-- Stationary/unarmed ground object so DCS instantiates external-light services.
GT.attribute = {
    wsType_Ground,
    wsType_Tank,
    wsType_NoWeapon,
    wsType_GenericFort,
    "Fortifications",
}
GT.category = "Fortification"

GT.shape_table_data = {
    {
        file = "TPG_Electrical_Substation_V1_LIGHTS",
        life = 1200,
        username = "TPG_Electrical_Substation_V1_LIGHTS",
        desrt = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed",
        classname = "lLandVehicle",
        positioning = "BYNORMAL",
    },
    {
        name = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed",
        file = "TPG_Electrical_Substation_V1_LIGHTS_Destroyed",
    }
}

local flood_lights = {}
local projector_proto = nil
if lamp_prototypes then
    projector_proto = lamp_prototypes.LFS_P_27_1000 or lamp_prototypes.LFS_P_27_200
end

for i = 0, 8 do
    local c = "TPG_YARD_FLOOD_" .. i

    if projector_proto then
        -- Current DCS projector form. Do NOT set intensity_max here: the prototype
        -- owns projector output. Previous tests incorrectly clamped this to 20/24.
        flood_lights[#flood_lights + 1] = {
            typename = "Spot",
            connector = c,
            proto = projector_proto,
            range = 110.0,
            angle_min = math.rad(18.0),
            angle_max = math.rad(68.0),
            exposure = {{25, 0.075, 0.085}},
            movable = false,
            power_up_t = 0.01,
            use_full_connector_position = true,
            color = {1.0, 0.78, 0.56},
        }
    else
        -- Compatibility fallback matching the older DCS spotlight table family,
        -- this time at real floodlight output instead of the failed 12/20 values.
        flood_lights[#flood_lights + 1] = {
            typename = "spotlight",
            connector = c,
            intensity_max = 1500.0,
            color = {1.0, 0.78, 0.56},
            angle_max = math.rad(68.0),
            pos_correction = {0, 0, 0},
            use_full_connector_position = true,
            dont_change_color = true,
            angle_change_rate = 0,
        }
    end

    -- Real ambient fill around each fixture. This is intentionally far stronger
    -- than a 3.0 navigation light but much weaker than the projected flood.
    flood_lights[#flood_lights + 1] = {
        typename = "omnilight",
        connector = c,
        intensity_max = 35.0,
        color = {1.0, 0.70, 0.46},
        pos_correction = {0, 0, 0},
        use_full_connector_position = true,
    }
end

local controller = {
    typename = "collection",
    lights = {
        [1] = {
            typename = "collection",
            lights = flood_lights,
        },
    },
}

-- Different DCS object families have historically looked at one or the other.
-- Assign both to the same controller rather than maintaining divergent tables.
GT.lights = controller
GT.lights_data = controller

add_surface_unit(GT)
GT = nil
'@
Set-Content -Path (Join-Path $db "db_tpg_electrical_substation_lights.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Electrical Substation V1.0 LIGHTS v1.1.0 PROJECTOR
======================================================

INSTALL
Delete/replace any older folder named:
  TPG_Electrical_Substation_V1_LIGHTS

Then copy this folder into:
  Saved Games\DCS\Mods\tech\

This LIGHTS edition coexists with the untouched original:
  TPG_Electrical_Substation_V1

MISSION EDITOR
Ground Units -> Fortification -> TPG Electrical Substation V1.0 LIGHTS

WHAT CHANGED
- Same high-fidelity substation layout and geometry.
- Nine actual EDM connectors are embedded in the visible intact model and both LODs.
- Each connector is aimed inward/down into the yard.
- Warm emissive lens geometry is added to all nine existing lamp heads.
- ZERO embedded Blender Light nodes, avoiding DCS 2.9.29 "Wrong light version".
- Projected lights use DCS current typename="Spot" + lamp_prototypes projector form.
- The failed Build 9 intensity_max=24 clamp is removed; projector output now comes from
  LFS_P_27_1000 (or LFS_P_27_200 fallback).
- Each fixture also has a 35-intensity omni fill for obvious local ambient spill.
- Destroyed model intentionally has no connectors/emissive lenses.

This is not another invisible light-only overlay and does not require a second object.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
