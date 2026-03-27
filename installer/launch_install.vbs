Set shell = CreateObject("WScript.Shell")
base = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & base & "\install_app.ps1"" -SourceExePath """ & base & "\DeviceHealthMonitorPRO.exe"" -UninstallScriptPath """ & base & "\uninstall_app.ps1"" -UninstallLauncherPath """ & base & "\launch_uninstall.vbs"""
shell.Run command, 0, True
