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
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Tacoma Recon"),
    version = "1.0.0",
    state = "installed",
    info = _("2016 Toyota Tacoma TRD Off Road 4x4 DCLB custom scout/recon vehicle")
})

mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")

dofile(current_mod_path.."/Database/db_tpg_tacoma_recon.lua")

plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
GT_t.CH_t.TPG_TACOMA_RECON = {
    life = 4.0,
    mass = 2500,
    length = 5.728,
    width = 1.895,

    -- Requested 113 mph road speed.
    -- 113 mph = 181.856 km/h = 50.5156 m/s.
    max_road_velocity = 50.5156,

    max_slope = 0.55,
    engine_power = 21000,
    gear_count = 6,
    canSwim = false,
    canWade = true,
    waterline_level = 0.20,
    fordingDepth = 0.55,
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
    armour_thickness = 0.002,
}

GT = {};
GT_t.ws = 0;

set_recursive_metatable(GT, GT_t.generic_wheel_vehicle);
set_recursive_metatable(GT.chassis, GT_t.CH_t.TPG_TACOMA_RECON);

GT.visual.shape = "TPG_Tacoma_Recon";
GT.visual.shape_dstr = "TPG_Tacoma_Recon_Destroyed";
GT.visual.positioning = "BYNORMAL";

GT.animation_arguments.wheels_rotation = 8;
GT.animation_arguments.wheels_turn_angle = 9;

GT.swing_on_run = false;
GT.mobile = true;
GT.Crew = 1;

GT.armour_scheme = unarmed_armour_scheme;

GT.visual.fire_size = 0.65;
GT.visual.fire_pos = {0.0, 0.75, 0.0};
GT.visual.fire_time = 420;
GT.time_agony = 12;

-- Scout/recon role: unarmed visual observer vehicle.
GT.sensor = {};
set_recursive_metatable(GT.sensor, GT_t.SN_visual);
GT.sensor.height = 1.75;
GT.sensor.max_range_finding_target = 5000;

GT.driverViewPoint = {0.72, 1.55, -0.32};
GT.CustomAimPoint = {0.0, 1.15, 0.0};

GT.Name = "TPG_Tacoma_Recon";
GT.DisplayName = _("Scout/Recon - 2016 Tacoma TRD Off Road DCLB");
GT.Rate = 8;

GT.DetectionRange = 5000;
GT.ThreatRange = 0;
GT.mapclasskey = "P0091000005";

GT.attribute = {
    wsType_Ground,
    wsType_Tank,
    wsType_NoWeapon,
    wsTypeKAMAZ_Tent,
    "Trucks",
    "Unarmed",
    "Scout",
    "Reconnaissance",
};

-- DCS ground-vehicle category list does not expose a dedicated Scout/Recon
-- top-level ME category, so this remains in the valid Unarmed category while
-- carrying explicit Scout/Recon attributes and DisplayName.
GT.category = "Unarmed";

-- Keep the requested speed visible to the Mission Editor in km/h.
GT.MaxSpeed = 181.856;

add_surface_unit(GT);
'@
Set-Content -Path (Join-Path $db "db_tpg_tacoma_recon.lua") -Value $dbLua -Encoding UTF8

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
