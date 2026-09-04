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
    version = "1.0.2-LIGHTS-FORT",
    state = "installed",
    info = _("High-detail electrical substation registered as an immobile Fortification so DCS services its yard lights")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_electrical_substation_lights.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
-- LIGHTS edition deliberately uses the full stationary Ground Unit/Fortification
-- registration path.  The visual asset is still completely immobile and unarmed,
-- but this causes DCS to instantiate the unit-side light controller used by working
-- light towers and other illuminated stationary ground equipment.
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

-- Critical difference from the failed Static/Structures registrations.
-- This remains a stationary, zero-mobility, no-weapon object, but DCS sees it via
-- the same Ground Unit -> Fortification path used by illuminated light-tower assets.
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

local yard_lights = {}
for i = 0, 8 do
    yard_lights[#yard_lights + 1] = {
        typename = "spotlight",
        connector = "TPG_YARD_SPOT_" .. i,
        color = {1.0, 0.82, 0.58},
        intensity_max = 12.0,
        angle_max = math.rad(38),
        dont_change_color = true,
        angle_change_rate = 0,
    }
end

-- Keep an explicit top-level collection, matching DCS light-data conventions,
-- rather than handing the runtime only a bare numbered subcollection.
GT.lights = {
    typename = "collection",
    lights = {
        [1] = {
            typename = "collection",
            lights = yard_lights,
        },
    },
}

add_surface_unit(GT)
GT = nil
'@
Set-Content -Path (Join-Path $db "db_tpg_electrical_substation_lights.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Electrical Substation V1.0 LIGHTS v1.0.2
=============================================

Install:
Copy the folder "TPG_Electrical_Substation_V1_LIGHTS" into:
  Saved Games\DCS\Mods\tech\

This version coexists with:
  TPG_Electrical_Substation_V1

Mission Editor placement for this corrected build:
  Ground Units -> Fortification -> TPG Electrical Substation V1.0 LIGHTS

Important:
- It is intentionally registered as a stationary Fortification rather than a plain Static Structure.
- It has a STATIC chassis, no weapons, no detection/threat capability and no usable mobility.
- This registration is specifically to make DCS instantiate the unit-side lighting controller.

LIGHTS v1.0.2:
- Same high-fidelity substation geometry/layout
- Nine existing yard fixtures retain named EDM connectors
- DCS unit-side light collection drives nine warm spotlights
- EDM lamp lenses remain self-illuminated
- Embedded EDM spot lights remain as a secondary fallback
- Destroyed model has no active connector/spot lights
- Original non-LIGHTS static-structure edition remains unchanged and can coexist
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHTS_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
