param(
    [string]$Python = (Join-Path $PSScriptRoot "venv\\Scripts\\python.exe")
)

if (-not (Test-Path $Python)) {
    throw "Python executable not found at $Python"
}

& $Python -m PyInstaller --noconfirm --clean (Join-Path $PSScriptRoot "DeviceHealthMonitorPRO.spec")
