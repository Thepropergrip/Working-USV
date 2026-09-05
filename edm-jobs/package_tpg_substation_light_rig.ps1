$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$src = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG.edm"
if (-not (Test-Path $src)) { throw "Missing light rig EDM" }

# Three physical copies keep each registration path independent while preserving
# the same proven connector-only EDM geometry.
Copy-Item $src (Join-Path $shapes "TPG_Electrical_Substation_V1_LIGHT_RIG.edm") -Force
Copy-Item $src (Join-Path $shapes "TPG_Electrical_Substation_V1_LIGHT_RIG_LOAD_TEST.edm") -Force
Copy-Item $src (Join-Path $shapes "TPG_Electrical_Substation_V1_LIGHT_RIG_PROTO_TEST.edm") -Force

if (Test-Path (Join-Path $root "Textures")) {
    Copy-Item (Join-Path $root "Textures\*") $textures -Force
}

$entry = @'
declare_plugin("TPG Electrical Substation V1.0 LIGHT RIG BUILD 9",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Electrical Substation V1.0 LIGHT RIG BUILD 9"),
    version = "1.0.4-PROJECTOR-PROTO",
    state = "installed",
    info = _("Diagnostic load test, legacy connector test, and modern lamp-prototype projector test; no embedded EDM light nodes")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_substation_light_rig.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
-- BUILD 9: the connector-only EDM is already proven to load in DCS 2.9.29.27468.
-- LOAD TEST confirms geometry/emissive only.
-- LIGHT TEST preserves the old lowercase spotlight syntax as a control.
-- PROTO LIGHT TEST uses the newer DCS Spot + lamp_prototypes projector form used by
-- current light-data examples. There are still ZERO embedded EDM SpotLight/OmniLight nodes.

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

local function make_fortification(name, display_name, shape_name, light_controller)
    local g = {}
    GT_t.ws = 0
    set_recursive_metatable(g, GT_t.generic_stationary)
    set_recursive_metatable(g.chassis, GT_t.CH_t.STATIC)

    g.chassis.life = 100000
    g.visual.shape = shape_name
    g.visual.fire_size = 0.0
    g.visual.fire_pos = {0, 0, 0}
    g.visual.fire_time = 0
    g.time_agony = 0

    g.Name = name
    g.DisplayName = _(display_name)
    g.Rate = 1
    g.DetectionRange = 0
    g.ThreatRange = 0
    g.mapclasskey = "P0091000076"
    g.positioning = "BYNORMAL"
    g.CustomAimPoint = {0, 4.0, 0}

    g.attribute = {
        wsType_Ground,
        wsType_Tank,
        wsType_NoWeapon,
        wsType_GenericFort,
        "Fortifications",
    }
    g.category = "Fortification"

    g.shape_table_data = {
        {
            file = shape_name,
            life = 100000,
            username = name,
            classname = "lLandVehicle",
            positioning = "BYNORMAL",
        }
    }

    g.lights = light_controller
    g.lights_data = light_controller
    add_surface_unit(g)
end

-- TEST B: Build-8 control using the older lowercase spotlight definition.
local legacy_yard_lights = {}
for i = 0, 8 do
    legacy_yard_lights[#legacy_yard_lights + 1] = {
        typename = "spotlight",
        connector = "TPG_YARD_SPOT_" .. i,
        color = {1.0, 0.82, 0.58},
        intensity_max = 20.0,
        angle_max = math.rad(40),
        dont_change_color = true,
        angle_change_rate = 0,
    }
end
local legacy_controller = {
    typename = "collection",
    lights = {
        [1] = { typename = "collection", lights = legacy_yard_lights },
    },
}
make_fortification(
    "TPG_Electrical_Substation_V1_LIGHT_RIG",
    "TPG Substation Light Rig LIGHT TEST (legacy)",
    "TPG_Electrical_Substation_V1_LIGHT_RIG",
    legacy_controller
)

-- TEST C: modern projector definition. Recent DCS light-data examples use typename
-- "Spot" together with an explicit lamp prototype. LFS_P_27_1000 is the standard
-- high-output landing-light projector prototype widely used in DCS light definitions.
local projector_proto = nil
if lamp_prototypes then
    projector_proto = lamp_prototypes.LFS_P_27_1000
end

local proto_yard_lights = {}
for i = 0, 8 do
    local l = {
        typename = "Spot",
        connector = "TPG_YARD_SPOT_" .. i,
        color = {1.0, 0.82, 0.58},
        intensity_max = 24.0,
        range = 120.0,
        angle_max = math.rad(42),
        angle_min = math.rad(18),
        dont_change_color = true,
        angle_change_rate = 0,
        movable = false,
        power_up_t = 0.0,
    }
    if projector_proto then
        l.proto = projector_proto
    end
    proto_yard_lights[#proto_yard_lights + 1] = l
end
local proto_controller = {
    typename = "collection",
    lights = {
        [1] = { typename = "collection", lights = proto_yard_lights },
    },
}
make_fortification(
    "TPG_Electrical_Substation_V1_LIGHT_RIG_PROTO_TEST",
    "TPG Substation Light Rig PROTO LIGHT TEST",
    "TPG_Electrical_Substation_V1_LIGHT_RIG_PROTO_TEST",
    proto_controller
)
'@
Set-Content -Path (Join-Path $db "db_tpg_substation_light_rig.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Electrical Substation V1.0 LIGHT RIG BUILD 9
=================================================

WHAT BUILD 8 PROVED
- The connector-only EDM now loads correctly in DCS.
- The visible lamp heads glow at night because of emissive material.
- The old connector/Lua spotlight control does not project illumination onto terrain/objects.

BUILD 9 TESTS

A) LOAD TEST
Static Objects -> Structures -> TPG Substation Light Rig LOAD TEST
Geometry + emissive material only. No projected light expected.

B) LIGHT TEST (legacy)
Ground Units -> Fortification -> TPG Substation Light Rig LIGHT TEST (legacy)
Build-8 lowercase spotlight syntax retained as the control.

C) PROTO LIGHT TEST
Ground Units -> Fortification -> TPG Substation Light Rig PROTO LIGHT TEST
Uses newer typename="Spot" plus lamp_prototypes.LFS_P_27_1000, 120 m range,
42 degree outer cone, and the same nine proven EDM connectors.
This is the test intended to produce actual terrain/object illumination.

There are ZERO embedded Blender/EDM light nodes in every variant.

Install:
Delete/replace the previous folder, then install:
  Saved Games\DCS\Mods\tech\TPG_Electrical_Substation_V1_LIGHT_RIG
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Electrical_Substation_V1_LIGHT_RIG_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Packaged $zip"
