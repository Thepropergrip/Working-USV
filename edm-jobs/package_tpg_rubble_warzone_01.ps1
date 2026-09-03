$ErrorActionPreference = "Stop"

$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Warzone_Rubble_Pile_01"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"

if (Test-Path $pkg) { Remove-Item $pkg -Recurse -Force }
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$models = @(
  "TPG_Warzone_Rubble_Pile_01.edm",
  "TPG_Warzone_Rubble_Pile_01_Destroyed.edm",
  "TPG_Warzone_Rubble_Pile_01_LOD1.edm",
  "TPG_Warzone_Rubble_Pile_01_LOD2.edm"
)

foreach ($m in $models) {
  $src = Join-Path $root $m
  if (-not (Test-Path $src)) { throw "Missing required model: $m" }
  if ((Get-Item $src).Length -le 0) { throw "Empty EDM: $m" }
  Copy-Item $src $shapes -Force
}

$lods = @'
model={
    lods={
        {"TPG_Warzone_Rubble_Pile_01.edm",450.0};
        {"TPG_Warzone_Rubble_Pile_01_LOD1.edm",1400.0};
        {"TPG_Warzone_Rubble_Pile_01_LOD2.edm",5000.0};
    };
    collision_shell="TPG_Warzone_Rubble_Pile_01.edm";
}
'@
Set-Content -Path (Join-Path $shapes "TPG_Warzone_Rubble_Pile_01.lods") -Value $lods -Encoding ASCII

$srcTex = Join-Path $root "Textures"
if (-not (Test-Path $srcTex)) { throw "Texture artifact folder missing." }
Copy-Item (Join-Path $srcTex "*") $textures -Force
if (-not (Get-ChildItem $textures -File)) { throw "No textures copied into package." }

$entry = @'
declare_plugin("TPG Warzone Rubble Pile 01",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Warzone Rubble Pile 01"),
    version = "1.0.0",
    state = "installed",
    info = _("High-detail 20x20-foot-class warzone building rubble and debris static asset")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_warzone_rubble_01.lua")
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
    Name = "TPG_Warzone_Rubble_Pile_01",
    DisplayName = _("TPG Warzone Rubble Pile 01"),
    ShapeName = "TPG_Warzone_Rubble_Pile_01",
    ShapeNameDestr = "TPG_Warzone_Rubble_Pile_01_Destroyed",
    Life = 180,
    Rate = 100,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_warzone_rubble_01.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Warzone Rubble Pile 01
==========================

Install:
Copy the folder "TPG_Warzone_Rubble_Pile_01" into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Warzone Rubble Pile 01

Design:
- Roughly 20 x 20 ft / 6.1 x 6.1 m warzone building-rubble mound
- Shattered concrete and masonry
- Broken slabs and beams
- Hollow cinder blocks
- Exposed and tangled rusted rebar
- Broken concrete and steel utility pipes
- Corrugated sheet metal
- Rusted wheel rim and half-buried tire
- Broken timber/pallet material
- Civilian/construction trash including plastic and cardboard debris
- Deliberately irregular, non-procedural-looking composition
- No visible terrain/base plane and no raised foundation
- Low debris extends slightly below placement z=0 to avoid a floating edge without creating terrain z-fighting
- Dedicated simplified collision shells
- LOD1 and LOD2
- Separate more dispersed/scorched destruction state

Technical:
- Blender 4.1.1
- Official Eagle Dynamics Blender EDM exporter
- DCS EDM materials with albedo and roughness/metallic texture data
- Material-batched static visual meshes
- UV validation on exported visual meshes
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Warzone_Rubble_Pile_01_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal

# Package integrity checks: exactly one top-level mod folder in the ZIP.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$z = [System.IO.Compression.ZipFile]::OpenRead($zip)
try {
  $tops = $z.Entries | ForEach-Object {
    $n = $_.FullName.Replace("\","/")
    if ($n.Contains("/")) { $n.Split("/")[0] } else { $n }
  } | Where-Object { $_ } | Sort-Object -Unique
  if ($tops.Count -ne 1 -or $tops[0] -ne "TPG_Warzone_Rubble_Pile_01") {
    throw "ZIP nesting validation failed: $($tops -join ', ')"
  }
}
finally { $z.Dispose() }

Get-Item $zip | ForEach-Object { Write-Host "FINAL PACKAGE: $($_.FullName) $($_.Length) bytes" }
