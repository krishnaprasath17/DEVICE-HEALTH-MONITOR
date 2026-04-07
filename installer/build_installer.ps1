param(
    [string]$SourceExe
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$distExe = if ($SourceExe) { $SourceExe } else { Join-Path $projectRoot "dist\DeviceHealthMonitor.exe" }
$stagingRoot = Join-Path $projectRoot "build\installer_staging"
$outputRoot = Join-Path $projectRoot "dist"
$sedPath = Join-Path $projectRoot "build\DeviceHealthMonitorInstaller.sed"
$outputExe = Join-Path $outputRoot "DeviceHealthMonitorSetup.exe"
$iexpressPath = Join-Path $env:WINDIR "System32\iexpress.exe"

if (-not (Test-Path $distExe)) {
    throw "Build the desktop EXE first: $distExe"
}
if (-not (Test-Path $iexpressPath)) {
    throw "IExpress is not available on this machine."
}

Remove-Item $stagingRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $sedPath) | Out-Null
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$stageFiles = @(
    @{ Source = $distExe; Name = "DeviceHealthMonitor.exe" },
    @{ Source = (Join-Path $projectRoot "public_base_url.txt"); Name = "public_base_url.txt" },
    @{ Source = (Join-Path $PSScriptRoot "install_app.ps1"); Name = "install_app.ps1" },
    @{ Source = (Join-Path $PSScriptRoot "uninstall_app.ps1"); Name = "uninstall_app.ps1" },
    @{ Source = (Join-Path $PSScriptRoot "launch_install.vbs"); Name = "launch_install.vbs" },
    @{ Source = (Join-Path $PSScriptRoot "launch_uninstall.vbs"); Name = "launch_uninstall.vbs" }
)

foreach ($file in $stageFiles) {
    Copy-Item -Path $file.Source -Destination (Join-Path $stagingRoot $file.Name) -Force
}

$targetName = $outputExe.Replace("\", "\\")
$sourceRoot = ($stagingRoot + "\").Replace("\", "\\")

$sedContent = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$targetName
FriendlyName=Device Health Monitor Setup
AppLaunched=wscript.exe launch_install.vbs
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[SourceFiles]
SourceFiles0=$sourceRoot
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
%FILE3%=
%FILE4%=
%FILE5%=
[Strings]
FILE0=DeviceHealthMonitor.exe
FILE1=public_base_url.txt
FILE2=install_app.ps1
FILE3=uninstall_app.ps1
FILE4=launch_install.vbs
FILE5=launch_uninstall.vbs
"@

[System.IO.File]::WriteAllText($sedPath, $sedContent, [System.Text.Encoding]::ASCII)

$process = Start-Process -FilePath $iexpressPath -ArgumentList "/N", $sedPath -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path $outputExe)) {
    throw "IExpress failed to build the installer."
}

Write-Output $outputExe
