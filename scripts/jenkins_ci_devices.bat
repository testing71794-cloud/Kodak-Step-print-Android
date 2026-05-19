@echo off
setlocal EnableExtensions
if "%~1"=="" (
  echo ERROR: %~nx0 requires workspace root as first argument.
  exit /b 1
)
cd /d "%~1"
call "%~dp0list_devices.bat" "%~1" || (
  echo 1> "device_detection_failed.flag"
  echo 1> "pipeline_failed.flag"
  exit /b 1
)
exit /b 0
