$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$mod = Join-Path $root "TPG_CGAXR_MC_Drone_Static"
$shapes = Join-Path $mod "Shapes"
$textures = Join-Path $mod "Textures"
$db = Join-Path $mod "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$edm = Join-Path $root "CGAXR_MC_Drone.edm"
if (-not (Test-Path $edm)) { throw "CGAXR_MC_Drone.edm not found." }
Copy-Item $edm (Join-Path $shapes "CGAXR_MC_Drone.edm") -Force

$sourceRoot = Join-Path $env:GITHUB_WORKSPACE "edm-jobs\cgaxr_mc_drone\mod"
foreach ($f in @("entry.lua","Database\CGAXR_MC_Drone_Static.lua","Shapes\CGAXR_MC_Drone.lods")) {
  $src = Join-Path $sourceRoot $f
  if (-not (Test-Path $src)) { throw "Missing packaging source: $src" }
  $dst = Join-Path $mod $f
  New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
  Copy-Item $src $dst -Force
}

$generatedTextures = Join-Path $root "Textures"
if (Test-Path $generatedTextures) {
  Copy-Item (Join-Path $generatedTextures "*") $textures -Force -Recurse
}

$zip = Join-Path $root "TPG_CGAXR_MC_Drone_Static_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $mod -DestinationPath $zip -CompressionLevel Optimal
Write-Host "PACKAGED: $zip"
