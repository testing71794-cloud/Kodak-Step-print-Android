@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Run the reduced editing suite: ED_01 + merged ED_02.
REM Usage: run_editing_verify_suite.bat [DEVICE_SERIAL]

set "DEVICE=%~1"
if "%DEVICE%"=="" set "DEVICE=ZA222RFQ75"
set "REPO_ROOT=%~dp0..\..\.."
cd /d "%REPO_ROOT%"

set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"
set "LOG=%REPO_ROOT%\reports\editing\verify_suite_%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%.log"
set "LOG=%LOG: =0%"

if not exist "%REPO_ROOT%\reports\editing" mkdir "%REPO_ROOT%\reports\editing"

echo Editing verify suite device=%DEVICE% > "%LOG%"
echo Started: %DATE% %TIME% >> "%LOG%"
echo. >> "%LOG%"

call :run_maestro "ED_01 - Enter edit photo mode.yaml"
call :run_maestro "ED_02 - Apply filter to photo.yaml"

echo. >> "%LOG%"
echo Finished: %DATE% %TIME% >> "%LOG%"
type "%LOG%"
exit /b 0

:run_maestro
set "FLOW=%~1"
echo === %FLOW% ===
echo === %FLOW% === >> "%LOG%"
call "%MAESTRO_BIN%" --device %DEVICE% test --reinstall-driver "ATP TestCase Flows\editing\%FLOW%"
set "RC=!ERRORLEVEL!"
if "!RC!"=="0" (
  echo %FLOW%: PASS>> "%LOG%"
) else (
  echo %FLOW%: FAIL rc=!RC!>> "%LOG%"
)
exit /b 0
