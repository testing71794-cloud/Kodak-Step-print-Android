@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ED_04 rotate: Maestro-only split (Adjust submenu -> imageViewRotate).
REM   ED_04a (before screenshot) -> ED_04b (rotate + confirm) -> AI verify
REM Usage: run_ed04_verify.bat [DEVICE_SERIAL]

set "REPO_ROOT=%~dp0..\..\.."
cd /d "%REPO_ROOT%"

set "DEVICE=%~1"
if "%DEVICE%"=="" set "DEVICE=ZA222RFQ75"
set "MAESTRO_DEVICE=%DEVICE%"

set "JAVA_HOME_FALLBACK=C:\Program Files\Eclipse Adoptium\jdk-25.0.2.10-hotspot"
if not defined JAVA_HOME if exist "%JAVA_HOME_FALLBACK%\bin\java.exe" set "JAVA_HOME=%JAVA_HOME_FALLBACK%"

set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"
set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
if not exist "%ADB%" set "ADB=adb"

if not exist "%MAESTRO_BIN%" (
  echo ERROR: Maestro not found at %MAESTRO_BIN%
  exit /b 1
)

"%ADB%" devices -l | findstr /I "%DEVICE%" >nul
if errorlevel 1 (
  echo ERROR: Device %DEVICE% not found
  exit /b 1
)

echo [INFO] ED_04 rotate path: ED_04a - ED_04b
call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "ATP TestCase Flows\editing\ED_04a - Rotate canvas ready.yaml"
if errorlevel 1 exit /b 1

call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "ATP TestCase Flows\editing\ED_04b - Rotate apply and verify.yaml"
set "MAESTRO_RC=!ERRORLEVEL!"
if not "!MAESTRO_RC!"=="0" (
  echo ERROR: ED_04b failed exit=!MAESTRO_RC!
  exit /b !MAESTRO_RC!
)

set "OPENROUTER_SSL_VERIFY=0"
where py >nul 2>&1
if not errorlevel 1 (
  echo [INFO] OpenRouter AI verify rotate...
  py -3 "%REPO_ROOT%\scripts\verify_ed_visual_pair.py" --profile ED_04
  set "VERIFY_RC=!ERRORLEVEL!"
  if not "!VERIFY_RC!"=="0" (
    echo WARN: ED_04 rotate AI verify returned !VERIFY_RC!
  )
)

echo [OK] ED_04 verify completed
exit /b 0
