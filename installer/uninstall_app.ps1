$ErrorActionPreference = "Stop"

$appName = "Device Health Monitor PRO"
$appId = "DeviceHealthMonitorPRO"
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"
$startMenuFolder = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$appName"
$uninstallKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$appId"
$dataRoot = Join-Path $env:LOCALAPPDATA "DeviceHealthMonitorPRO"
$shell = New-Object -ComObject WScript.Shell

function Show-Popup {
    param(
        [string]$Message,
        [int]$Flags = 0x40
    )
    return $shell.Popup($Message, 0, $appName, $Flags)
}

$runningProcess = Get-Process -Name "DeviceHealthMonitorPRO" -ErrorAction SilentlyContinue
if ($runningProcess) {
    Show-Popup "Close Device Health Monitor PRO before uninstalling it.", 0x10 | Out-Null
    exit 1
}

if (Test-Path $desktopShortcutPath) {
    Remove-Item $desktopShortcutPath -Force -ErrorAction SilentlyContinue
}
if (Test-Path $startMenuFolder) {
    Remove-Item $startMenuFolder -Recurse -Force -ErrorAction SilentlyContinue
}
if (Test-Path $uninstallKeyPath) {
    Remove-Item $uninstallKeyPath -Recurse -Force -ErrorAction SilentlyContinue
}

$cleanupScript = Join-Path $env:TEMP "dhm_cleanup.cmd"
$cleanupContent = @"
@echo off
ping 127.0.0.1 -n 3 >nul
rmdir /s /q "$installRoot"
del /q "%~f0"
"@
[System.IO.File]::WriteAllText($cleanupScript, $cleanupContent, [System.Text.Encoding]::ASCII)
Start-Process -FilePath (Join-Path $env:WINDIR "System32\cmd.exe") -ArgumentList "/c", "`"$cleanupScript`"" -WindowStyle Hidden

Show-Popup "Device Health Monitor PRO has been removed from this laptop.`n`nSaved Google sign-in data and settings were kept here:`n$dataRoot" 0x40 | Out-Null
exit 0
