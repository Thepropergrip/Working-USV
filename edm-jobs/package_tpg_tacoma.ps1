$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Tacoma_Recon"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"

if (Test-Path $pkg) { Remove-Item $pkg -Recurse -Force }
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
  throw "No Tacoma textures generated."
}

$entry = @'
declare_plugin("TPG Tacoma Recon", {
    displayName = _("TPG Tacoma Recon"),
    shortName = "TPG Tacoma Recon",
    installed = true,
    dirName = current_mod_path,
    fileMenuName = _("TPG Tacoma Recon"),
    version = "3.0.0",
    state = "installed",
    developerName = "TPG",
    info = _("2016 Toyota Tacoma TRD Off Road 4x4 DCLB custom scout/recon ground vehicle."),
})

mount_vfs_model_path(current_mod_path .. "/Shapes")
mount_vfs_texture_path(current_mod_path .. "/Textures")

dofile(current_mod_path .. "/Database/TPG_Tacoma_Recon.lua")

plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$vehicle = @'
GT_t.CH_t.TPG_TACOMA_RECON = {
    life = 4.0,
    mass = 2500,
    length = 5.728,
    width = 1.895,
    max_road_velocity = 50.5156, -- 113 mph / 181.856 km/h

    max_slope = 0.47,
    canSwim = false,
    canWade = true,
    fordingDepth = 0.55,
    engine_power = 278,
    engineMinRPM = 600,
    engineMaxPowerRPM = 4600,
    engineMaxRPM = 6200,
    gearRatios = {-3.52, 0.0, 3.60, 2.09, 1.49, 1.00, 0.69, 0.58},
    mainGearRatio = 3.91,
    automaticTransmission = true,

    max_vert_obstacle = 0.35,
    max_acceleration = 4.2,
    min_turn_radius = 5.8,

    X_gear_1 = 1.7855,
    Y_gear_1 = 0.0,
    Z_gear_1 = 0.405,
    X_gear_2 = -1.7855,
    Y_gear_2 = 0.0,
    Z_gear_2 = 0.405,

    gear_type = GT_t.GEAR_TYPES.WHEELS,
    r_max = 0.405,
    armour_thickness = 0.001,
}

GT = {}
GT_t.ws = 0

-- Proven registration path from the user's working ME build.
set_recursive_metatable(GT, GT_t.generic_wheel_IFV)
set_recursive_metatable(GT.chassis, GT_t.CH_t.TPG_TACOMA_RECON)

GT.visual.shape = "TPG_Tacoma_Recon"
GT.visual.shape_dstr = "TPG_Tacoma_Recon_Destroyed"

GT.swing_on_run = false
GT.turbine = false

GT.visual.fire_size = 0.30
GT.visual.fire_pos[1] = 0.0
GT.visual.fire_pos[2] = 0.75
GT.visual.fire_pos[3] = 0.0
GT.visual.fire_time = 240
GT.visual.min_time_agony = 3
GT.visual.max_time_agony = 15

GT.Name = "TPG_Tacoma_Recon"
GT.DisplayName = _("[TPG] Tacoma Scout/Recon")
GT.DisplayNameShort = _("Tacoma Recon")
GT.Rate = 3

GT.DetectionRange = 0
GT.ThreatRange = 0
GT.mapclasskey = "P0091000002"

GT.attribute = {
    wsType_Ground, wsType_Tank, wsType_Gun, WSTYPE_PLACEHOLDER,
    "Armed ground units", "LightArmoredUnits", "APC", "IFV",
}
GT.category = "Armor"
GT.tags = {"Armor", "APC", "IFV", "Scout/Recon"}
GT.Countries = {"USA"}

add_surface_unit(GT)
'@
Set-Content -Path (Join-Path $db "TPG_Tacoma_Recon.lua") -Value $vehicle -Encoding UTF8

$readme = @'
TPG Tacoma Recon v3.0 — FBX Quality Rebuild
===========================================

INSTALL
Delete any older TPG_Tacoma_Recon folder.
Copy the single TPG_Tacoma_Recon folder directly into:
  Saved Games\DCS\Mods\tech\

MISSION EDITOR
Ground Units -> Armor -> [TPG] Tacoma Scout/Recon

V3 MODEL BASIS
The rejected procedural v2 body is no longer the vehicle foundation. V3 uses the
supplied 2016 Tacoma FBX body geometry and preserves the proven DCS registration.

Reference locked to the user's photographs:
- 2016 Toyota Tacoma TRD Off Road 4x4 DCLB
- Quicksand (4T8)
- paint-matched camper shell
- black tubular rock sliders
- low-profile black roof/platform racks
- Black Oak cowl/ditch lights
- stock-height stance
- TRD Off Road style wheels / all-terrain tires
- black fender flares
- slim front LED bar present in the supplied FBX/reference front
- custom rear bumper
- amber auxiliary reverse/backup lights
- fictional DCS plate, not the owner's real plate
- no invented weapons or recon equipment

V3 QA FIXES
- FBX wheel transforms corrected to the actual 3.571 m wheelbase
- front/rear wheel centers aligned with the chassis declaration
- front steering and all-wheel roll use DCS arguments 9 and 8
- neutral export is frame 100
- tube sliders and cowl-light brackets are baked to mesh for EDM export
- camper shell is shaped/tapered instead of the rejected rectangular block
- rack support feet prevent the prior floating-rack appearance
- rear bumper is positioned behind the body shell
- side/rear text is baked to mesh rather than left as unsupported Blender font objects

PERFORMANCE
113 mph = 181.856 km/h = 50.5156 m/s
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Tacoma_Recon_v3.0_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal

if (-not (Test-Path $zip)) { throw "Final Tacoma ZIP not created." }
Write-Host "FINAL PACKAGE: $zip $((Get-Item $zip).Length) bytes"
