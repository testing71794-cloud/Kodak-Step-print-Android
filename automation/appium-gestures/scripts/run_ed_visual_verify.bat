@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Generic Maestro split + OpenRouter verify for visual editing tests.
REM Usage: run_ed_visual_verify.bat PROFILE FLOW_A FLOW_B [DEVICE_SERIAL]
REM Example: run_ed_visual_verify.bat ED_07 "ED_07a - Temperature canvas ready.yaml" "ED_07b - Temperature apply and verify.yaml"

set "PROFILE=%~1"
set "FLOW_A=%~2"
set "FLOW_B=%~3"
set "DEVICE=%~4"
if "%DEVICE%"=="" set "DEVICE=ZA222RFQ75"

if "%PROFILE%"=="" goto :usage
if "%FLOW_A%"=="" goto :usage
if "%FLOW_B%"=="" goto :usage

set "REPO_ROOT=%~dp0..\..\.."
cd /d "%REPO_ROOT%"

set "MAESTRO_DEVICE=%DEVICE%"
set "JAVA_HOME_FALLBACK=C:\Program Files\Eclipse Adoptium\jdk-25.0.2.10-hotspot"
if not defined JAVA_HOME if exist "%JAVA_HOME_FALLBACK%\bin\java.exe" set "JAVA_HOME=%JAVA_HOME_FALLBACK%"

set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"
set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
if not exist "%ADB%" set "ADB=adb"

if not exist "%MAESTRO_BIN%" (
  echo ERROR: Maestro not found
  exit /b 1
)

"%ADB%" devices -l | findstr /I "%DEVICE%" >nul
if errorlevel 1 (
  echo ERROR: Device %DEVICE% not found
  exit /b 1
)

echo [INFO] %PROFILE% path: %FLOW_A% -^> %FLOW_B%
call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "ATP TestCase Flows\editing\%FLOW_A%"
if errorlevel 1 exit /b 1

call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "ATP TestCase Flows\editing\%FLOW_B%"
set "MAESTRO_RC=!ERRORLEVEL!"
if not "!MAESTRO_RC!"=="0" (
  echo ERROR: %FLOW_B% failed exit=!MAESTRO_RC!
  exit /b !MAESTRO_RC!
)

set "OPENROUTER_SSL_VERIFY=0"
where py >nul 2>&1
if not errorlevel 1 (
  echo [INFO] OpenRouter AI verify %PROFILE%...
  py -3 "%REPO_ROOT%\scripts\verify_ed_visual_pair.py" --profile %PROFILE%
  set "VERIFY_RC=!ERRORLEVEL!"
  if not "!VERIFY_RC!"=="0" (
    echo WARN: %PROFILE% AI verify returned !VERIFY_RC!
    exit /b !VERIFY_RC!
  )
)

echo [OK] %PROFILE% verify completed
exit /b 0

:usage
echo Usage: run_ed_visual_verify.bat PROFILE FLOW_A FLOW_B [DEVICE_SERIAL]
exit /b 2
