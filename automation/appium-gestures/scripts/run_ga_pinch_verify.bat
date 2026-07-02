@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Gallery pinch with REAL two-finger Appium W3C multitouch.
REM   Maestro (GA_05a/GA_06a) -> Appium pinch -> Maestro (GA_05b/GA_06b)
REM Usage:
REM   run_ga_pinch_verify.bat pinch-out [DEVICE]   REM GA_06 zoom in (spread)
REM   run_ga_pinch_verify.bat pinch-in  [DEVICE]   REM GA_05 zoom out (pinch together)

set "GESTURE=%~1"
set "DEVICE=%~2"
if /I "%GESTURE%"=="zoom-in" set "GESTURE=pinch-out"
if /I "%GESTURE%"=="zoom-out" set "GESTURE=pinch-in"
if /I "%GESTURE%"=="ga06" set "GESTURE=pinch-out"
if /I "%GESTURE%"=="ga05" set "GESTURE=pinch-in"

if "%GESTURE%"=="" (
  echo Usage: run_ga_pinch_verify.bat ^<pinch-out^|pinch-in^|ga06^|ga05^> [DEVICE_SERIAL]
  exit /b 1
)

set "REPO_ROOT=%~dp0..\..\.."
cd /d "%REPO_ROOT%"

if /I "%GESTURE%"=="pinch-out" (
  set "FLOW_A=ATP TestCase Flows\gallery\GA_06a - Gallery photo ready for Appium pinch.yaml"
  set "FLOW_B=ATP TestCase Flows\gallery\GA_06b - Gallery after pinch verify.yaml"
  set "CASE_ID=GA_06"
) else if /I "%GESTURE%"=="pinch-in" (
  set "FLOW_A=ATP TestCase Flows\gallery\GA_05a - Gallery photo ready for Appium pinch.yaml"
  set "FLOW_B=ATP TestCase Flows\gallery\GA_05b - Gallery after pinch verify.yaml"
  set "CASE_ID=GA_05"
) else (
  echo ERROR: Unknown gesture "%GESTURE%". Use pinch-out ^(GA_06 zoom in^) or pinch-in ^(GA_05 zoom out^).
  exit /b 1
)

set "JAVA_HOME_FALLBACK=C:\Program Files\Eclipse Adoptium\jdk-25.0.2.10-hotspot"
if not defined JAVA_HOME if exist "%JAVA_HOME_FALLBACK%\bin\java.exe" set "JAVA_HOME=%JAVA_HOME_FALLBACK%"

if exist "C:\Program Files\nodejs\node.exe" set "PATH=C:\Program Files\nodejs;C:\Tools\npm-global;%PATH%"
if exist "C:\Tools\npm-global" set "PATH=C:\Tools\npm-global;%PATH%"
if not defined NODE_HOME if exist "C:\Program Files\nodejs\node.exe" set "NODE_HOME=C:\Program Files\nodejs"

set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"
if defined ATP_MAESTRO_PARALLEL_HOME if exist "%ATP_MAESTRO_PARALLEL_HOME%\maestro.bat" set "MAESTRO_BIN=%ATP_MAESTRO_PARALLEL_HOME%\maestro.bat"
if defined MAESTRO_HOME if exist "%MAESTRO_HOME%\maestro.bat" set "MAESTRO_BIN=%MAESTRO_HOME%\maestro.bat"
if not exist "%MAESTRO_BIN%" set "MAESTRO_BIN=C:\Users\HP\maestro\maestro\bin\maestro.bat"
if not defined ANDROID_HOME set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
if not defined ANDROID_SDK_ROOT set "ANDROID_SDK_ROOT=%ANDROID_HOME%"
if defined ANDROID_HOME if exist "%ANDROID_HOME%\platform-tools\adb.exe" (
  set "ADB=%ANDROID_HOME%\platform-tools\adb.exe"
) else if defined ADB_HOME if exist "%ADB_HOME%\adb.exe" (
  set "ADB=%ADB_HOME%\adb.exe"
) else (
  set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
)
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
echo [INFO] %CASE_ID% Appium W3C path gesture=%GESTURE% device=%DEVICE%

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

echo [INFO] %CASE_ID%: Maestro pre-pinch ^(!FLOW_A!^)
call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "!FLOW_A!"
if errorlevel 1 exit /b 1

echo [INFO] Waiting for Maestro to release UiAutomation...
ping 127.0.0.1 -n 4 >nul

if "!PINCH_MODE!"=="appium" (
  set "GALLERY_PINCH=1"
  set "PINCH_STYLE=diagonal"
  if /I "!CASE_ID!"=="GA_05" (
    echo [INFO] GA_05: diagonal pinch-out ^(zoom in setup^) then pinch-in ^(zoom out^)
    call "%MODULE_DIR%\examples\scripts\run_pinch_zoom_w3c.bat" pinch-out %DEVICE%
    if errorlevel 1 exit /b 2
    ping 127.0.0.1 -n 2 >nul
    call "%MODULE_DIR%\examples\scripts\run_pinch_zoom_w3c.bat" pinch-in %DEVICE%
  ) else (
    echo [INFO] Appium W3C two-finger %GESTURE% ^(real multitouch^) for !CASE_ID!
    call "%MODULE_DIR%\examples\scripts\run_pinch_zoom_w3c.bat" %GESTURE% %DEVICE%
  )
) else (
  echo ERROR: Appium not on PATH. Parallel adb swipe is NOT real pinch.
  echo Install: npm install -g appium ^& appium driver install uiautomator2
  exit /b 2
)
if errorlevel 1 (
  echo ERROR: Pinch gesture failed
  exit /b 2
)

echo [INFO] Resetting adb so Maestro can reconnect for post-pinch verify...
"%ADB%" reconnect >nul 2>&1
ping 127.0.0.1 -n 5 >nul

echo [INFO] %CASE_ID%: Maestro post-pinch ^(!FLOW_B!^)
call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "!FLOW_B!"
set "MAESTRO_RC=!ERRORLEVEL!"
if not "!MAESTRO_RC!"=="0" (
  echo ERROR: %CASE_ID% post-pinch Maestro failed exit=!MAESTRO_RC!
  exit /b !MAESTRO_RC!
)

echo [OK] %CASE_ID% completed gesture=%GESTURE% pinch_mode=!PINCH_MODE!
echo [INFO] W3C screenshots: automation\appium-gestures\target\screenshots\w3c\
exit /b 0
