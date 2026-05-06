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