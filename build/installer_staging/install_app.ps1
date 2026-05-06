param(
    [string]$SourceExePath,
    [string]$PublicBaseUrlPath,
    [string]$UninstallScriptPath,
    [string]$UninstallLauncherPath,
    [string]$InstallRoot
)

$ErrorActionPreference = "Stop"

$appName = "Device Health Monitor"
$appId = "DeviceHealthMonitor"
$publisher = "Krishna Prasath M"
$defaultInstallRoot = Join-Path $env:LOCALAPPDATA "Programs\Device Health Monitor"
$defaultDataRoot = Join-Path $env:LOCALAPPDATA "DeviceHealthMonitor"
$desktopShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"
$startMenuFolder = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$appName"
$startMenuShortcutPath = Join-Path $startMenuFolder "$appName.lnk"
$uninstallShortcutPath = Join-Path $startMenuFolder "Uninstall $appName.lnk"
$uninstallKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$appId"
$shell = New-Object -ComObject WScript.Shell

function Show-Popup {
    param(
        [string]$Message,
        [int]$Flags = 0x40
    )
    return $shell.Popup($Message, 0, $appName, $Flags)
}

function New-ShortcutFile {
    param(
        [string]$ShortcutPath,
        [string]$TargetPath,
        [string]$Arguments = "",
        [string]$WorkingDirectory = "",
        [string]$IconLocation = "",
        [string]$Description = ""
    )
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    if ($Arguments) {
        $shortcut.Arguments = $Arguments
    }
    if ($WorkingDirectory) {
        $shortcut.WorkingDirectory = $WorkingDirectory
    }
    if ($IconLocation) {
        $shortcut.IconLocation = $IconLocation
    }
    if ($Description) {
        $shortcut.Description = $Description
    }
    $shortcut.Save()
}

function Test-WebView2RuntimeInstalled {
    $clientId = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    $registryPaths = @(
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$clientId",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$clientId",
        "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$clientId"
    )
    foreach ($path in $registryPaths) {
        try {
            $value = (Get-ItemProperty -Path $path -ErrorAction Stop).pv
            if ($value) {
                return $true
            }
        } catch {
        }
    }
    return $false
}

if (-not $InstallRoot) {
    $InstallRoot = $defaultInstallRoot
}

if ([string]::IsNullOrWhiteSpace($SourceExePath) -or -not (Test-Path $SourceExePath)) {
    throw "The application EXE was not found in the setup package."
}
if ([string]::IsNullOrWhiteSpace($PublicBaseUrlPath) -or -not (Test-Path $PublicBaseUrlPath)) {
    throw "The public base URL file was not found in the setup package."
}
if ([string]::IsNullOrWhiteSpace($UninstallScriptPath) -or -not (Test-Path $UninstallScriptPath)) {
    throw "The uninstall script was not found in the setup package."
}
if ([string]::IsNullOrWhiteSpace($UninstallLauncherPath) -or -not (Test-Path $UninstallLauncherPath)) {
    throw "The uninstall launcher was not found in the setup package."
}

$runningProcess = Get-Process -Name "DeviceHealthMonitor" -ErrorAction SilentlyContinue
if ($runningProcess) {
    Show-Popup "Close Device Health Monitor before running setup again.", 0x10 | Out-Null
    exit 1
}

$resolvedSourceExe = (Resolve-Path $SourceExePath).Path
$resolvedPublicBaseUrl = (Resolve-Path $PublicBaseUrlPath).Path
$resolvedUninstallScript = (Resolve-Path $UninstallScriptPath).Path
$resolvedUninstallLauncher = (Resolve-Path $UninstallLauncherPath).Path

$exeTargetPath = Join-Path $InstallRoot "DeviceHealthMonitor.exe"
$publicBaseUrlTarget = Join-Path $InstallRoot "public_base_url.txt"
$uninstallScriptTarget = Join-Path $InstallRoot "uninstall_app.ps1"
$uninstallLauncherTarget = Join-Path $InstallRoot "launch_uninstall.vbs"

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
New-Item -ItemType Directory -Force -Path $startMenuFolder | Out-Null
New-Item -ItemType Directory -Force -Path $defaultDataRoot | Out-Null

Copy-Item -Path $resolvedSourceExe -Destination $exeTargetPath -Force
Copy-Item -Path $resolvedPublicBaseUrl -Destination $publicBaseUrlTarget -Force
Copy-Item -Path $resolvedUninstallScript -Destination $uninstallScriptTarget -Force
Copy-Item -Path $resolvedUninstallLauncher -Destination $uninstallLauncherTarget -Force

New-ShortcutFile `
    -ShortcutPath $desktopShortcutPath `
    -TargetPath $exeTargetPath `
    -WorkingDirectory $InstallRoot `
    -IconLocation $exeTargetPath `
    -Description "Open $appName"

New-ShortcutFile `
    -ShortcutPath $startMenuShortcutPath `
    -TargetPath $exeTargetPath `
    -WorkingDirectory $InstallRoot `
    -IconLocation $exeTargetPath `
    -Description "Open $appName"

New-ShortcutFile `
    -ShortcutPath $uninstallShortcutPath `
    -TargetPath (Join-Path $env:WINDIR "System32\wscript.exe") `
    -Arguments "`"$uninstallLauncherTarget`"" `
    -WorkingDirectory $InstallRoot `
    -IconLocation $exeTargetPath `
    -Description "Uninstall $appName"

$estimatedSizeKb = [math]::Ceiling((Get-Item $exeTargetPath).Length / 1KB)
New-Item -Path $uninstallKeyPath -Force | Out-Null
Set-ItemProperty -Path $uninstallKeyPath -Name "DisplayName" -Value $appName
Set-ItemProperty -Path $uninstallKeyPath -Name "DisplayVersion" -Value (Get-Date -Format "yyyy.MM.dd")
Set-ItemProperty -Path $uninstallKeyPath -Name "Publisher" -Value $publisher
Set-ItemProperty -Path $uninstallKeyPath -Name "InstallLocation" -Value $InstallRoot
Set-ItemProperty -Path $uninstallKeyPath -Name "DisplayIcon" -Value $exeTargetPath
Set-ItemProperty -Path $uninstallKeyPath -Name "UninstallString" -Value "`"$env:WINDIR\System32\wscript.exe`" `"$uninstallLauncherTarget`""
Set-ItemProperty -Path $uninstallKeyPath -Name "QuietUninstallString" -Value "`"$env:WINDIR\System32\wscript.exe`" `"$uninstallLauncherTarget`""
Set-ItemProperty -Path $uninstallKeyPath -Name "NoModify" -Value 1 -Type DWord
Set-ItemProperty -Path $uninstallKeyPath -Name "NoRepair" -Value 1 -Type DWord
Set-ItemProperty -Path $uninstallKeyPath -Name "EstimatedSize" -Value $estimatedSizeKb -Type DWord

$warning = ""
if (-not (Test-WebView2RuntimeInstalled)) {
    $warning = "`n`nMicrosoft Edge WebView2 Runtime was not detected. Install it if the app window does not open on this laptop."
}

$launchResult = Show-Popup "Device Health Monitor is installed.`n`nInstalled to:`n$InstallRoot`n`nSaved app data will be stored in:`n$defaultDataRoot$warning`n`nOpen the app now?" 0x24
if ($launchResult -eq 6) {
    Start-Process -FilePath $exeTargetPath -WorkingDirectory $InstallRoot
}

exit 0
