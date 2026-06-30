@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ED_03 with REAL two-finger pinch (Appium W3C or parallel ADB multitouch).
REM   ED_03a (Maestro) -> pinch -> ED_03b (Maestro) -> AI verify
REM Pinch priority: Appium > ADB parallel (never Maestro swipe-only for this script)
REM Usage: run_ed03_verify.bat [DEVICE_SERIAL]

set "REPO_ROOT=%~dp0..\..\.."
cd /d "%REPO_ROOT%"

set "DEVICE=%~1"

set "JAVA_HOME_FALLBACK=C:\Program Files\Eclipse Adoptium\jdk-25.0.2.10-hotspot"
if not defined JAVA_HOME if exist "%JAVA_HOME_FALLBACK%\bin\java.exe" set "JAVA_HOME=%JAVA_HOME_FALLBACK%"

if exist "C:\Program Files\nodejs\node.exe" set "PATH=C:\Program Files\nodejs;C:\Users\%USERNAME%\AppData\Roaming\npm;%PATH%"

set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"
set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
if not defined ANDROID_HOME set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
if not defined ANDROID_SDK_ROOT set "ANDROID_SDK_ROOT=%ANDROID_HOME%"
set "MODULE_DIR=%REPO_ROOT%\automation\appium-gestures"
set "PINCH_MODE=adb"

if not exist "%ADB%" set "ADB=adb"

if "%DEVICE%"=="" (
  for /f "skip=1 tokens=1" %%D in ('"%ADB%" devices 2^>nul') do (
    if "%%D" neq "" (
      set "DEVICE=%%D"
      goto :device_ok
    )
  )
  set "DEVICE=ZA222RFQ75"
)
:device_ok
set "ANDROID_SERIAL=%DEVICE%"
set "MAESTRO_DEVICE=%DEVICE%"
echo [INFO] Device: %DEVICE%

if not exist "%MAESTRO_BIN%" (
  echo ERROR: Maestro not found at %MAESTRO_BIN%
  exit /b 1
)

"%ADB%" devices -l | findstr /I "%DEVICE%" >nul
if errorlevel 1 (
  echo ERROR: Device %DEVICE% not found
  exit /b 1
)

echo [INFO] Ensuring adb + Maestro driver are ready...
"%ADB%" reconnect >nul 2>&1
ping 127.0.0.1 -n 3 >nul

where appium >nul 2>&1
if not errorlevel 1 set "PINCH_MODE=appium"

if "!PINCH_MODE!"=="appium" (
  set "APPIUM_PORT=4723"
  netstat -an | findstr /C:":!APPIUM_PORT! " | findstr LISTENING >nul 2>&1
  if errorlevel 1 (
    echo [INFO] Starting Appium on port !APPIUM_PORT! ...
    start "Appium" /B cmd /c "set ANDROID_HOME=%ANDROID_HOME%&& set ANDROID_SDK_ROOT=%ANDROID_SDK_ROOT%&& set APPIUM_SKIP_CHROMEDRIVER_INSTALL=1&& appium --address 127.0.0.1 --port !APPIUM_PORT!"
    ping 127.0.0.1 -n 8 >nul
  )
)

echo [INFO] ED_03 real pinch path (video 29): ED_03a detail preview - !PINCH_MODE! pinch - ED_03b verify
call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "ATP TestCase Flows\editing\ED_03a - Fit crop canvas ready.yaml"
if errorlevel 1 exit /b 1

echo [INFO] Waiting for Maestro to release UiAutomation...
ping 127.0.0.1 -n 4 >nul

if "!PINCH_MODE!"=="appium" (
  echo [INFO] Using Appium W3C two-finger pinch ^(real multitouch^)
  call "%MODULE_DIR%\examples\scripts\run_pinch_zoom_w3c.bat" pinch-out %DEVICE%
) else (
  echo ERROR: Appium not on PATH. Parallel adb swipe is NOT real pinch.
  echo Install: npm install -g appium ^& appium driver install uiautomator2
  exit /b 2
)
if errorlevel 1 (
  echo ERROR: Pinch gesture failed
  exit /b 2
)

echo [INFO] Resetting adb so Maestro can reconnect for ED_03b...
"%ADB%" reconnect >nul 2>&1
ping 127.0.0.1 -n 5 >nul

set "OPENROUTER_SSL_VERIFY=0"
if not defined OPENROUTER_MODEL_VISION set "OPENROUTER_MODEL_VISION=openai/gpt-4.1-mini"
where py >nul 2>&1
if not errorlevel 1 (
  echo [INFO] Verify photo detail pinch ^(model=%OPENROUTER_MODEL_VISION%^)...
  py -3 "%REPO_ROOT%\scripts\verify_ed03_detail_pinch_ai.py"
  set "PINCH_AI_RC=!ERRORLEVEL!"
  if not "!PINCH_AI_RC!"=="0" (
    echo WARN: Photo detail pinch AI verify returned !PINCH_AI_RC!
  )
)

call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "ATP TestCase Flows\editing\ED_03b - Fit crop pan exit.yaml"
set "MAESTRO_RC=!ERRORLEVEL!"

if not "!MAESTRO_RC!"=="0" (
  echo ERROR: ED_03b failed exit=!MAESTRO_RC!
  exit /b !MAESTRO_RC!
)

set "OPENROUTER_SSL_VERIFY=0"
if not defined OPENROUTER_MODEL_VISION set "OPENROUTER_MODEL_VISION=openai/gpt-4.1-mini"
where py >nul 2>&1
if not errorlevel 1 (
  echo [INFO] OpenRouter AI verify ^(model=%OPENROUTER_MODEL_VISION%^)...
  py -3 "%REPO_ROOT%\scripts\verify_ed03_fit_crop_screen_ai.py"
)

echo [OK] ED_03 verify completed pinch=!PINCH_MODE!
exit /b 0
