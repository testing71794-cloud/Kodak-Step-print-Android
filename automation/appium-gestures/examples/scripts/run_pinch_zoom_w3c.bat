@echo off
setlocal EnableExtensions
REM True two-finger pinch via Appium W3C Actions (Node + WebdriverIO).
set "MODULE_DIR=%~dp0..\.."
set "GESTURE=%~1"
set "DEVICE=%~2"
if "%GESTURE%"=="" set "GESTURE=both"

if not defined NPM_GLOBAL set "NPM_GLOBAL=C:\Tools\npm-global"
if not defined NODE_HOME if exist "C:\Program Files\nodejs\node.exe" set "NODE_HOME=C:\Program Files\nodejs"
if defined NODE_HOME set "PATH=%NODE_HOME%;%PATH%"
if exist "%NPM_GLOBAL%" set "PATH=%NPM_GLOBAL%;%PATH%"
if not defined ANDROID_HOME if defined ADB_HOME (
  for %%I in ("%ADB_HOME%\..") do set "ANDROID_HOME=%%~fI"
)
if not defined ANDROID_HOME set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
for %%I in ("%ANDROID_HOME%") do set "ANDROID_HOME=%%~fI"
if not defined ANDROID_SDK_ROOT set "ANDROID_SDK_ROOT=%ANDROID_HOME%"

set "NODE_EXE=node"
if defined NODE_HOME if exist "%NODE_HOME%\node.exe" set "NODE_EXE=%NODE_HOME%\node.exe"
if not exist "%NODE_EXE%" if exist "C:\Program Files\nodejs\node.exe" set "NODE_EXE=C:\Program Files\nodejs\node.exe"

cd /d "%MODULE_DIR%"
if not exist "node_modules\webdriverio" (
  echo [INFO] Installing webdriverio...
  call npm install --no-fund --no-audit
  if errorlevel 1 exit /b 1
)

set "ANDROID_SERIAL=%DEVICE%"
echo [INFO] W3C pinch: gesture=%GESTURE% device=%DEVICE% node=%NODE_EXE% GALLERY_PINCH=%GALLERY_PINCH%
"%NODE_EXE%" scripts\pinch_w3c.mjs %GESTURE% %DEVICE%
exit /b %ERRORLEVEL%
