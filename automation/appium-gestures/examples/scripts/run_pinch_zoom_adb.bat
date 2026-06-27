@echo off
REM Wrapper for PowerShell ADB parallel pinch (true two-finger input).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_pinch_zoom_adb.ps1" -Gesture "%~1" -Device "%~2"
exit /b %ERRORLEVEL%
