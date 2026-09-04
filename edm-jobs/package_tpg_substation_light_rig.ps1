$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$src = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG.edm"
if (-not (Test-Path $src)) { throw "Missing light rig EDM" }

# Two physical copies avoid any ambiguity from registering one model file through
# both the Static Structure and Ground Unit/Fortification code paths.
Copy-Item $src (Join-Path $shapes "TPG_Electrical_Substation_V1_LIGHT_RIG.edm") -Force
Copy-Item $src (Join-Path $shapes "TPG_Electrical_Substation_V1_LIGHT_RIG_LOAD_TEST.edm") -Force

if (Test-Path (Join-Path $root "Textures")) {
    Copy-Item (Join-Path $root "Textures\*") $textures -Force
}

$entry = @'
declare_plugin("TPG Electrical Substation V1.0 LIGHT RIG BUILD 8",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Electrical Substation V1.0 LIGHT RIG BUILD 8"),
    version = "1.0.3-CONNECTOR-ONLY",
    state = "installed",
    info = _("Diagnostic load-test and connector-only light-test assets; no embedded EDM light nodes")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_substation_light_rig.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
-- BUILD 8 deliberately contains NO embedded EDM SpotLight/OmniLight nodes.
-- DCS 2.9.29.27468 rejected those with "Wrong light version".
-- This package exposes two independent tests using the same visible diagnostic mast geometry.

-- TEST A: plain static structure. If this is visible, the EDM/material/bounds path is healthy.
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
    Name = "TPG_Electrical_Substation_V1_LIGHT_RIG_LOAD_TEST",
    DisplayName = _("TPG Substation Light Rig LOAD TEST"),
    ShapeName = "TPG_Electrical_Substation_V1_LIGHT_RIG_LOAD_TEST",
    Life = 100000,
    Rate = 1,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})

-- TEST B: stationary Fortification. This is the DCS-managed connector-light path.
GT = {}
GT_t.ws = 0
set_recursive_metatable(GT, GT_t.generic_stationary)
set_recursive_metatable(GT.chassis, GT_t.CH_t.STATIC)

GT.chassis.life = 100000
GT.visual.shape = "TPG_Electrical_Substation_V1_LIGHT_RIG"
GT.visual.fire_size = 0.0
GT.visual.fire_pos = {0, 0, 0}
GT.visual.fire_time = 0
GT.time_agony = 0

GT.Name = "TPG_Electrical_Substation_V1_LIGHT_RIG"
GT.DisplayName = _("TPG Substation Light Rig LIGHT TEST")
GT.Rate = 1
GT.DetectionRange = 0
GT.ThreatRange = 0
GT.mapclasskey = "P0091000076"
GT.positioning = "BYNORMAL"
GT.CustomAimPoint = {0, 4.0, 0}

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
        file = "TPG_Electrical_Substation_V1_LIGHT_RIG",
        life = 100000,
        username = "TPG_Electrical_Substation_V1_LIGHT_RIG",
        classname = "lLandVehicle",
        positioning = "BYNORMAL",
    }
}

local yard_lights = {}
for i = 0, 8 do
    yard_lights[#yard_lights + 1] = {
        typename = "spotlight",
        connector = "TPG_YARD_SPOT_" .. i,
        color = {1.0, 0.82, 0.58},
        intensity_max = 20.0,
        angle_max = math.rad(40),
        dont_change_color = true,
        angle_change_rate = 0,
    }
end

local light_controller = {
    typename = "collection",
    lights = {
        [1] = {
            typename = "collection",
            lights = yard_lights,
        },
    },
}

-- Different DCS object families have historically looked at different field names.
-- Supplying both references to the same table is harmless if one is ignored and
-- lets this diagnostic cover both conventions without exporting any EDM light node.
GT.lights = light_controller
GT.lights_data = light_controller

add_surface_unit(GT)
GT = nil
'@
Set-Content -Path (Join-Path $db "db_tpg_substation_light_rig.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Electrical Substation V1.0 LIGHT RIG BUILD 8
=================================================

WHY THIS BUILD EXISTS
DCS 2.9.29.27468 rejected both old- and current-exporter Blender EDM light nodes with:
  Reason: Wrong light version.

Build 8 removes that object type completely.
There are ZERO Blender/EDM SpotLight or OmniLight nodes in either test asset.

TEST A - MODEL LOAD ONLY
Mission Editor:
  Static Objects -> Structures -> TPG Substation Light Rig LOAD TEST

Expected:
  Nine obvious fluorescent-magenta ~8 m masts with orange bases and large lamp heads.
  No projected illumination is expected from this object.

TEST B - CONNECTOR LIGHTING
Mission Editor:
  Ground Units -> Fortification -> TPG Substation Light Rig LIGHT TEST

Expected:
  The same nine obvious magenta masts.
  DCS-side Lua spotlights are attached to nine EDM connectors named TPG_YARD_SPOT_0 through _8.
  No embedded EDM light objects are present.

Install:
Delete/replace the previous folder, then install:
  Saved Games\DCS\Mods\tech\TPG_Electrical_Substation_V1_LIGHT_RIG

For comparison with the normal substation, place the test object at the same coordinates and heading.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
