@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Run all editing visual-verify orchestrators + Maestro-only flows.
REM Usage: run_editing_verify_suite.bat [DEVICE_SERIAL]

set "DEVICE=%~1"
if "%DEVICE%"=="" set "DEVICE=ZA222RFQ75"
set "REPO_ROOT=%~dp0..\..\.."
cd /d "%REPO_ROOT%"

set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"
set "VISUAL=%REPO_ROOT%\automation\appium-gestures\scripts\run_ed_visual_verify.bat"
set "LOG=%REPO_ROOT%\reports\editing\verify_suite_%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%.log"
set "LOG=%LOG: =0%"

if not exist "%REPO_ROOT%\reports\editing" mkdir "%REPO_ROOT%\reports\editing"

echo Editing verify suite device=%DEVICE% > "%LOG%"
echo Started: %DATE% %TIME% >> "%LOG%"
echo. >> "%LOG%"

call :run_visual ED_02 "ED_02a - Filter canvas ready.yaml" "ED_02b - Filter apply and verify.yaml"
call :run_script run_ed03_verify.bat
call :run_visual ED_04 "ED_04a - Rotate canvas ready.yaml" "ED_04b - Rotate apply and verify.yaml"
call :run_visual ED_05 "ED_05a - Brightness canvas ready.yaml" "ED_05b - Brightness apply and verify.yaml"
call :run_visual ED_07 "ED_07a - Temperature canvas ready.yaml" "ED_07b - Temperature apply and verify.yaml"
call :run_visual ED_15 "ED_15a - Frame canvas ready.yaml" "ED_15b - Frame apply and verify.yaml"
call :run_visual ED_13 "ED_13a - Doodle canvas ready.yaml" "ED_13b - Doodle apply and verify.yaml"
call :run_visual ED_20 "ED_20a - Blur canvas ready.yaml" "ED_20b - Blur apply and verify.yaml"

call :run_maestro "ED_01 - Enter edit photo mode.yaml"
call :run_maestro "ED_06 - Adjust contrast.yaml"
call :run_maestro "ED_08 - Adjust saturation.yaml"
call :run_maestro "ED_09 - Adjust highlights.yaml"
call :run_maestro "ED_10 - Adjust shadows.yaml"
call :run_maestro "ED_12 - Add text to photo.yaml"
call :run_maestro "ED_18 - Save edited image to gallery.yaml"
call :run_maestro "ED_19 - Discard changes dont save.yaml"
call :run_maestro "ED_13 - Add doodle to photo.yaml"
call :run_maestro "ED_20 - Blur popup YES path.yaml"
call :run_maestro "ED_21 - Blur popup NO path.yaml"
call :run_maestro "ED_22 - NO BLUR removes blur effect.yaml"
call :run_maestro "ED_E02 - Multiple edits combined.yaml"

echo. >> "%LOG%"
echo Finished: %DATE% %TIME% >> "%LOG%"
type "%LOG%"
exit /b 0

:run_visual
set "ID=%~1"
set "A=%~2"
set "B=%~3"
echo === %ID% visual verify ===
echo === %ID% visual verify === >> "%LOG%"
call "%VISUAL%" %ID% "%A%" "%B%" %DEVICE%
set "RC=!ERRORLEVEL!"
if "!RC!"=="0" (
  echo %ID%: PASS>> "%LOG%"
) else (
  echo %ID%: FAIL rc=!RC!>> "%LOG%"
)
exit /b 0

:run_script
set "SCRIPT=%~1"
echo === %SCRIPT% ===
echo === %SCRIPT% === >> "%LOG%"
call "%REPO_ROOT%\automation\appium-gestures\scripts\%SCRIPT%" %DEVICE%
set "RC=!ERRORLEVEL!"
if "!RC!"=="0" (
  echo %SCRIPT%: PASS>> "%LOG%"
) else (
  echo %SCRIPT%: FAIL rc=!RC!>> "%LOG%"
)
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
