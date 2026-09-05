$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Tacoma_Recon"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$models = @(
  "TPG_Tacoma_Recon.edm",
  "TPG_Tacoma_Recon_Destroyed.edm",
  "TPG_Tacoma_Recon_LOD1.edm",
  "TPG_Tacoma_Recon_LOD2.edm"
)
foreach ($m in $models) {
  $src = Join-Path $root $m
  if (-not (Test-Path $src)) { throw "Missing required model: $m" }
  if ((Get-Item $src).Length -le 0) { throw "EDM is empty: $m" }
  Copy-Item $src $shapes -Force
}

$lods = @'
model={
    lods={
        {"TPG_Tacoma_Recon.edm",350.0};
        {"TPG_Tacoma_Recon_LOD1.edm",1000.0};
        {"TPG_Tacoma_Recon_LOD2.edm",6000.0};
    };
    collision_shell="TPG_Tacoma_Recon.edm";
}
'@
Set-Content -Path (Join-Path $shapes "TPG_Tacoma_Recon.lods") -Value $lods -Encoding ASCII

if (Test-Path (Join-Path $root "Textures")) {
    Copy-Item (Join-Path $root "Textures\*") $textures -Force
}
if (-not (Get-ChildItem $textures -File -ErrorAction SilentlyContinue)) {
    throw "No Tacoma textures were generated."
}

$entry = @'
declare_plugin("TPG Tacoma Recon",
{
    dirName       = current_mod_path,
    displayName   = _("TPG Tacoma Recon"),
    shortName     = "TPG_TACOMA",
    version       = "1.0.2",
    state         = "installed",
    installed     = true,
    developerName = "TPG",
    info          = _("2016 Toyota Tacoma TRD Off Road 4x4 DCLB custom scout/recon vehicle"),
})

mount_vfs_model_path   (current_mod_path .. "/Shapes")
mount_vfs_texture_path (current_mod_path .. "/Textures")

dofile(current_mod_path .. "/Database/db_vehicles.lua")

plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8


$chassisDir = Join-Path $db "Chassis"
$vehicleDir = Join-Path $db "Vehicles"
New-Item -ItemType Directory -Force -Path $chassisDir,$vehicleDir | Out-Null

$chassisLua = @'
GT_t.CH_t.tpg_tacoma_chassis = {
    life = 4.0,
    mass = 2500,
    length = 5.728,
    width = 1.895,
    max_road_velocity = 50.5156,
    max_slope = 0.47,
    canSwim = false,
    canWade = true,
    engine_power = 210,
    engineMinRPM = 600,
    engineMaxPowerRPM = 4600,
    engineMaxRPM = 6200,
    gearRatios = { -3.52, 0.0, 3.60, 2.09, 1.49, 1.00, 0.69, 0.58 },
    mainGearRatio = 3.91,
    automaticTransmission = true,
    max_vert_obstacle = 0.35,
    max_acceleration = 4.2,
    min_turn_radius = 5.8,
    X_gear_1 = 1.7855,
    Y_gear_1 = 0,
    Z_gear_1 = 0.405,
    X_gear_2 = -1.7855,
    Y_gear_2 = 0,
    Z_gear_2 = 0.405,
    gear_type = GT_t.GEAR_TYPES.WHEELS,
    r_max = 0.405,
    trace_width = 0.285,
    armour_thickness = 0.001,
}
'@
Set-Content -Path (Join-Path $chassisDir "tpg_tacoma_chassis.lua") -Value $chassisLua -Encoding UTF8

$vehicleLua = @'
GT = {};
GT_t.ws = 0;

set_recursive_metatable(GT, GT_t.generic_wheel_vehicle);
set_recursive_metatable(GT.chassis, GT_t.CH_t.tpg_tacoma_chassis);

GT.visual.shape = "TPG_Tacoma_Recon";
GT.visual.shape_dstr = "TPG_Tacoma_Recon_Destroyed";

GT.chassis.life = 4.0;
GT.swing_on_run = false;

GT.visual.fire_size = 0.25;
GT.visual.fire_pos[1] = 0.0;
GT.visual.fire_pos[2] = 0.75;
GT.visual.fire_pos[3] = 0.0;
GT.visual.fire_time = 360;
GT.visual.min_time_agony = 5;
GT.visual.max_time_agony = 10;

GT.Name = "TPG_Tacoma_Recon";
GT.DisplayName = _("TPG Tacoma Scout/Recon");
GT.DisplayNameShort = _("Tacoma Recon");
GT.Rate = 5;

GT.DetectionRange = 0;
GT.ThreatRange = 0;
GT.mapclasskey = "P0091000212";

GT.attribute = {
    wsType_Ground,
    wsType_Tank,
    wsType_NoWeapon,
    wsType_GenericVehicle,
    "Trucks",
};

GT.category = "Unarmed";

GT.tags = {
    "Unarmed",
    "Scout/Recon",
};

GT.Countries = {"USA"};
'@
Set-Content -Path (Join-Path $vehicleDir "tpg_tacoma.lua") -Value $vehicleLua -Encoding UTF8

$dbLua = @'
local plugin_db_path = current_mod_path .. "/Database/"

local function chassis_file(f)
    if dofile(plugin_db_path .. f) then
        error("can't load file " .. f)
        return
    end
end

local function vehicle_file(f)
    if dofile(plugin_db_path .. f) then
        error("can't load file " .. f)
        return
    end
    if GT then
        GT.shape_table_data =
        {
            {
                file        = GT.visual.shape;
                username    = GT.Name;
                desrt       = GT.visual.shape_dstr;
                classname   = "lLandVehicle";
                positioning = "BYNORMAL";
                life        = GT.life or 6;
            },
            {
                name = GT.visual.shape_dstr;
                file = GT.visual.shape_dstr;
            },
        }
        GT.MaxSpeed = GT.chassis and GT.chassis.max_road_velocity and (GT.chassis.max_road_velocity * 3.6)
        add_surface_unit(GT)
        GT = nil;
    else
        error("GT empty in file " .. f)
    end
end

GT = nil;
chassis_file("Chassis/tpg_tacoma_chassis.lua")
vehicle_file("Vehicles/tpg_tacoma.lua")
'@
Set-Content -Path (Join-Path $db "db_vehicles.lua") -Value $dbLua -Encoding UTF8


$readme = @'
TPG Tacoma Recon v1.0
====================

INSTALL
Copy the single folder "TPG_Tacoma_Recon" directly into:
  Saved Games\DCS\Mods\tech\

MISSION EDITOR
Ground Units -> Unarmed
Scout/Recon - 2016 Tacoma TRD Off Road DCLB

REFERENCE / LOCKED BUILD
- 2016 Toyota Tacoma TRD Off Road 4x4
- Double Cab Long Bed
- Quicksand (4T8)
- Photo-driven custom configuration
- Paint-matched camper shell
- Low-profile roof/platform racks
- Paired Black Oak hood/cowl ditch lights
- Stock-height photographed stance
- TRD Off Road style 16-in alloy wheels and all-terrain tires
- Black wheel flares
- Tube rock sliders
- Heavy-duty rear bumper
- Bright amber auxiliary backup lights recessed in rear bumper
- Fictional realistic DCS plate in place of the owner's real plate
- Dried road mud / wear treatment based on supplied photos
- No weapons or invented scout equipment

ANIMATION
- DCS ground-vehicle argument 8: wheel rotation
- DCS ground-vehicle argument 9: front-wheel steering
- Steering is separated from wheel-roll pivots to avoid wheel wobble.

PERFORMANCE
Requested maximum road speed:
  113 mph
  181.856 km/h
  50.5156 m/s

ASSET
- High-detail hero EDM
- Dedicated destroyed EDM
- LOD1
- LOD2
- Embedded low-complexity collision-shell geometry
- DCS EDM material textures
- Ground vehicle Lua registration
- Clean one-folder Mods\tech package
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

# Shipping cleanliness check: only runtime files/folders are placed in the mod.
$zip = Join-Path $root "TPG_Tacoma_Recon_v1.0_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal

if (-not (Test-Path $zip)) { throw "Final Tacoma ZIP was not created." }
Get-Item $zip | ForEach-Object {
    Write-Host "FINAL PACKAGE: $($_.FullName) $($_.Length) bytes"
}
