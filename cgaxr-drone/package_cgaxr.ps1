$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$mod = Join-Path $root "TPG_CGAXR_MC_Drone_Static"
$shapes = Join-Path $mod "Shapes"
$textures = Join-Path $mod "Textures"
$db = Join-Path $mod "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

Copy-Item (Join-Path $root "CGAXR_MC_Drone.edm") (Join-Path $shapes "CGAXR_MC_Drone.edm") -Force
Copy-Item (Join-Path $env:GITHUB_WORKSPACE "cgaxr-drone/mod-template/CGAXR_MC_Drone.lods") (Join-Path $shapes "CGAXR_MC_Drone.lods") -Force
Copy-Item (Join-Path $env:GITHUB_WORKSPACE "cgaxr-drone/mod-template/entry.lua") (Join-Path $mod "entry.lua") -Force
Copy-Item (Join-Path $env:GITHUB_WORKSPACE "cgaxr-drone/mod-template/db_CGAXR_MC_Drone.lua") (Join-Path $db "db_CGAXR_MC_Drone.lua") -Force
Get-ChildItem (Join-Path $root "Textures") -File | Copy-Item -Destination $textures -Force
Copy-Item (Join-Path $env:GITHUB_WORKSPACE "cgaxr-drone/SOURCE_AUDIT.md") (Join-Path $mod "SOURCE_AUDIT.md") -Force

$zip = Join-Path $root "TPG_CGAXR_MC_Drone_Static_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $mod -DestinationPath $zip -CompressionLevel Optimal
Write-Host "DCS drop-in: $zip"
Get-ChildItem -Recurse $mod | ForEach-Object { Write-Host $_.FullName }
