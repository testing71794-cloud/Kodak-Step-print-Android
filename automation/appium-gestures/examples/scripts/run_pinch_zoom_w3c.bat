@echo off
setlocal EnableExtensions
REM True two-finger pinch via Appium W3C Actions (Node + WebdriverIO).
set "MODULE_DIR=%~dp0..\.."
set "GESTURE=%~1"
set "DEVICE=%~2"
if "%GESTURE%"=="" set "GESTURE=both"

if not defined NODE_HOME if exist "C:\Program Files\nodejs\node.exe" set "PATH=C:\Program Files\nodejs;%PATH%"
if not defined ANDROID_HOME set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
if not defined ANDROID_SDK_ROOT set "ANDROID_SDK_ROOT=%ANDROID_HOME%"
cd /d "%MODULE_DIR%"
if not exist "node_modules\webdriverio" (
  echo [INFO] Installing webdriverio...
  call npm install --no-fund --no-audit
  if errorlevel 1 exit /b 1
)

set "ANDROID_SERIAL=%DEVICE%"
node scripts\pinch_w3c.mjs %GESTURE% %DEVICE%
exit /b %ERRORLEVEL%
