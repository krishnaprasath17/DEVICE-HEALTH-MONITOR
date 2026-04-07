param(
    [string]$Python = (Join-Path $PSScriptRoot "venv\\Scripts\\python.exe")
)

if (-not (Test-Path $Python)) {
    throw "Python executable not found at $Python"
}

$ErrorActionPreference = "Stop"

$specPath = Join-Path $PSScriptRoot "DeviceHealthMonitor.spec"
$portableRoot = Join-Path $PSScriptRoot "dist_portable"
$portableFolder = Join-Path $portableRoot "DeviceHealthMonitor-Portable"
$portableZip = Join-Path $portableRoot "DeviceHealthMonitor-Portable.zip"
$distExe = Join-Path $PSScriptRoot "dist\\DeviceHealthMonitor.exe"
$publicBaseUrl = Join-Path $PSScriptRoot "public_base_url.txt"
$portableMarker = Join-Path $portableFolder "portable_mode.flag"
$portableReadme = Join-Path $portableFolder "PORTABLE-README.txt"

& $Python -m PyInstaller --noconfirm --clean $specPath

if (-not (Test-Path $distExe)) {
    throw "Portable build failed because the EXE was not created: $distExe"
}

Remove-Item $portableFolder -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $portableZip -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $portableFolder | Out-Null

Copy-Item -Path $distExe -Destination (Join-Path $portableFolder "DeviceHealthMonitor.exe") -Force
if (Test-Path $publicBaseUrl) {
    Copy-Item -Path $publicBaseUrl -Destination (Join-Path $portableFolder "public_base_url.txt") -Force
}

[System.IO.File]::WriteAllText($portableMarker, "Portable mode enabled.`r`n", [System.Text.Encoding]::ASCII)
[System.IO.File]::WriteAllText(
    $portableReadme,
    @"
Device Health Monitor Portable
=================================

This portable build stores its settings, logs, Google sign-in data, and battery report files next to the EXE.

Files used by the portable build:
- portable_mode.flag
- public_base_url.txt
- notification_settings.json
- google_auth_state.bin
- app.log
- desktop_app.log

To move the portable app to another laptop:
1. Copy this whole folder.
2. Keep public_base_url.txt updated with your ngrok URL if you want phone access.
3. Run DeviceHealthMonitor.exe.
"@,
    [System.Text.Encoding]::ASCII
)

Compress-Archive -Path (Join-Path $portableFolder "*") -DestinationPath $portableZip -Force

Write-Output $portableFolder
Write-Output $portableZip
