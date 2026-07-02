@echo off

setlocal EnableExtensions EnableDelayedExpansion

REM Gallery pinch with REAL Appium mobile gestures.

REM   Maestro (ready subflow) -> Appium pinch -> vision verify (optional)

REM Usage:

REM   run_ga_pinch_verify.bat pinch-out [DEVICE]   REM GA_06 zoom IN only

REM   run_ga_pinch_verify.bat pinch-in  [DEVICE]   REM GA_05 zoom OUT only



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

  set "FLOW_PRE=ATP TestCase Flows\gallery\subflows\gallery_ready_for_appium_pinch_ga06.yaml"

  set "CASE_ID=GA_06"

  set "PINCH_GESTURE=pinch-out"

) else if /I "%GESTURE%"=="pinch-in" (

  set "FLOW_PRE=ATP TestCase Flows\gallery\subflows\gallery_ready_for_appium_pinch.yaml"

  set "CASE_ID=GA_05"

  set "PINCH_GESTURE=pinch-in"

) else (

  echo ERROR: Unknown gesture "%GESTURE%". Use pinch-out ^(GA_06 zoom in^) or pinch-in ^(GA_05 zoom out^).

  exit /b 1

)



set "JAVA_HOME_FALLBACK=C:\Program Files\Eclipse Adoptium\jdk-25.0.2.10-hotspot"

if not defined JAVA_HOME if exist "%JAVA_HOME_FALLBACK%\bin\java.exe" set "JAVA_HOME=%JAVA_HOME_FALLBACK%"



if not defined NPM_GLOBAL set "NPM_GLOBAL=C:\Tools\npm-global"

if not defined NODE_HOME if exist "C:\Program Files\nodejs\node.exe" set "NODE_HOME=C:\Program Files\nodejs"

if defined NODE_HOME set "PATH=%NODE_HOME%;%PATH%"

if exist "%NPM_GLOBAL%" set "PATH=%NPM_GLOBAL%;%PATH%"

if defined ADB_HOME for %%I in ("%ADB_HOME%") do if not defined ANDROID_HOME set "ANDROID_HOME=%%~dpI.."



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

echo [INFO] %CASE_ID% Appium path gesture=!PINCH_GESTURE! ^(%GESTURE%^) device=%DEVICE%



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



set "APPIUM_BIN="

if defined NPM_GLOBAL if exist "%NPM_GLOBAL%\appium.cmd" set "APPIUM_BIN=%NPM_GLOBAL%\appium.cmd"

if not defined APPIUM_BIN if exist "C:\Tools\npm-global\appium.cmd" set "APPIUM_BIN=C:\Tools\npm-global\appium.cmd"

if not defined APPIUM_BIN (

  where appium >nul 2>&1

  if not errorlevel 1 for /f "delims=" %%A in ('where appium 2^>nul') do if not defined APPIUM_BIN set "APPIUM_BIN=%%A"

)

if defined APPIUM_BIN set "PINCH_MODE=appium"

echo [INFO] PINCH_MODE=!PINCH_MODE! APPIUM_BIN=!APPIUM_BIN! NODE_HOME=!NODE_HOME! ANDROID_HOME=!ANDROID_HOME!



if "!PINCH_MODE!"=="appium" (

  set "APPIUM_PORT=4723"

  netstat -an | findstr /C:":!APPIUM_PORT! " | findstr LISTENING >nul 2>&1

  if errorlevel 1 (

    echo [INFO] Starting Appium on port !APPIUM_PORT! via "!APPIUM_BIN!" ...

    start "Appium" /B cmd /c "set ANDROID_HOME=%ANDROID_HOME%&& set ANDROID_SDK_ROOT=%ANDROID_SDK_ROOT%&& set APPIUM_SKIP_CHROMEDRIVER_INSTALL=1&& ""!APPIUM_BIN!"" --address 127.0.0.1 --port !APPIUM_PORT!"

    ping 127.0.0.1 -n 8 >nul

  ) else (

    echo [INFO] Appium already listening on port !APPIUM_PORT!

  )

) else (

  echo ERROR: Appium not found ^(expected %NPM_GLOBAL%\appium.cmd^). Run scripts\windows_agent\install_node_appium_for_jenkins.bat as Administrator.

  exit /b 2

)



echo [INFO] %CASE_ID%: Maestro pre-pinch ^(!FLOW_PRE!^)

call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "!FLOW_PRE!"

if errorlevel 1 exit /b 1



echo [INFO] Waiting for Maestro to release UiAutomation...

ping 127.0.0.1 -n 4 >nul



if "!PINCH_MODE!"=="appium" (
  set "GALLERY_PINCH=1"
  set "PINCH_STYLE=diagonal"
  set "PINCH_GESTURE_PERCENT=1.0"
  if /I "!CASE_ID!"=="GA_05" set "GALLERY_GA05_ZOOM_OUT=1"
  echo [INFO] %CASE_ID%: Appium !PINCH_GESTURE! only ^(no mixed gestures^)
  call "%MODULE_DIR%\examples\scripts\run_pinch_zoom_w3c.bat" !PINCH_GESTURE! %DEVICE%
) else (

  echo ERROR: PINCH_MODE was not appium — cannot run real pinch.

  exit /b 2

)

if errorlevel 1 (

  echo ERROR: Pinch gesture failed

  exit /b 2

)



set "OPENROUTER_SSL_VERIFY=0"

if not defined OPENROUTER_MODEL_VISION set "OPENROUTER_MODEL_VISION=openai/gpt-4.1-mini"

where py >nul 2>&1

if not errorlevel 1 (

  if /I "!CASE_ID!"=="GA_05" (

    echo [INFO] GA_05 vision verify zoom OUT ^(model=!OPENROUTER_MODEL_VISION!^)...

    py -3 "%REPO_ROOT%\scripts\verify_ga05_gallery_pinch_ai.py"

  ) else (

    echo [INFO] GA_06 vision verify zoom IN ^(model=!OPENROUTER_MODEL_VISION!^)...

    py -3 "%REPO_ROOT%\scripts\verify_ga06_gallery_pinch_ai.py"

  )

  set "PINCH_AI_RC=!ERRORLEVEL!"

  if not "!PINCH_AI_RC!"=="0" (

    echo ERROR: %CASE_ID% pinch did not visibly change the photo preview ^(vision verify exit=!PINCH_AI_RC!^)

    exit /b !PINCH_AI_RC!

  )

) else (

  if /I "!ATP_REQUIRE_PINCH_VISION!"=="1" (

    echo ERROR: py not found but ATP_REQUIRE_PINCH_VISION=1

    exit /b 3

  )

  echo WARN: py not found — %CASE_ID% passes without vision verify of zoom change

)



echo [OK] %CASE_ID% completed gesture=!PINCH_GESTURE! pinch_mode=!PINCH_MODE!

echo [INFO] W3C screenshots: automation\appium-gestures\target\screenshots\w3c\

exit /b 0


