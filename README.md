# Device Health Monitor PRO

Device Health Monitor PRO is a Windows desktop monitoring app built with Flask, pywebview, and PyInstaller. It shows live device health data inside a desktop window, keeps the backend hidden from the user, opens Google sign-in in the default browser, and delivers CPU and RAM alert emails to the signed-in Google account.

## What It Does

- Live desktop dashboard for CPU, RAM, disk, battery, and network activity
- Hidden local Flask backend inside the desktop app
- Google sign-in in browser, with the dashboard staying inside the app window
- CPU and RAM alert thresholds with cooldown control
- Battery charge bar, battery health bar, charging/disconnected state, and readable time left
- Windows battery report viewer inside the app
- Live history charts updating every 2 seconds
- Battery health trend chart for the last 7 available days
- Dark mode and light mode support
- Windows installer build with desktop and Start Menu shortcuts

## Install On Another Laptop

Use the installer included in this repository:

- `dist/DeviceHealthMonitorPROSetup.exe`

The installer:

- Installs the app to `%LOCALAPPDATA%\Programs\Device Health Monitor PRO`
- Creates Desktop and Start Menu shortcuts
- Registers an uninstall entry
- Stores app data in `%LOCALAPPDATA%\DeviceHealthMonitorPRO`

## Google OAuth Setup

The live Google OAuth client file is intentionally not committed to this repository.

To configure Google login:

1. Copy `google_oauth_client.example.json` to `google_oauth_client.json`
2. Replace the placeholder values with your Google OAuth web client values
3. Make sure this redirect URI is added in Google Cloud:

```text
http://127.0.0.1:5000/auth/google/callback
```

The app uses Google profile/email access and Gmail send access so alert emails can be sent from the signed-in Google account.

## Run From Source

### Python desktop app

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python desktop_app.py
```

### Flask backend only

```powershell
venv\Scripts\activate
python app.py
```

## Build The Desktop EXE

```powershell
venv\Scripts\activate
python -m PyInstaller --noconfirm --clean DeviceHealthMonitorPRO.spec
```

The generated desktop EXE will be created in:

```text
dist\DeviceHealthMonitorPRO.exe
```

## Build The Installer

After building the EXE, create the Windows installer with:

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build_installer.ps1
```

The generated installer will be created in:

```text
dist\DeviceHealthMonitorPROSetup.exe
```

## Main Files

- `app.py`: Flask backend, hardware telemetry, Google OAuth, alerts, battery report parsing
- `desktop_app.py`: pywebview desktop launcher with hidden backend behavior
- `templates/`: dashboard, login, and desktop auth-complete pages
- `installer/`: installer builder, install script, uninstall script, and hidden launchers
- `DeviceHealthMonitorPRO.spec`: PyInstaller build definition
- `requirements.txt`: Python dependencies

## Frontend Source Notes

This repository also contains the original Figma/Vite source bundle under `src/` and `package.json`. The currently shipped Windows desktop app uses the Flask templates in `templates/` as the active UI.

## Dependencies

Python dependencies are listed in `requirements.txt`, including:

- Flask
- psutil
- pywebview
- PyInstaller
- google-auth and Google API client libraries

## Attribution

See `ATTRIBUTIONS.md` for third-party attribution notes.
