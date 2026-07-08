@echo off

setlocal EnableExtensions EnableDelayedExpansion

REM Quick per-module editing checks (ED_Q1..ED_Q11) with OpenRouter AI after each key op.

REM Usage: run_quick_module_checks.bat [DEVICE_SERIAL] [Q#]
REM   run_quick_module_checks.bat ZA222RFQ75         -> all modules
REM   run_quick_module_checks.bat ZA222RFQ75 Q4      -> only ED_Q4

set "DEVICE=%~1"
if "%DEVICE%"=="" set "DEVICE=ZA222RFQ75"
set "ONLY=%~2"

set "REPO_ROOT=%~dp0..\..\.."
cd /d "%REPO_ROOT%"

set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"
if defined OPENROUTER_API_KEY if not defined OpenRouterAPI set "OpenRouterAPI=%OPENROUTER_API_KEY%"
set "MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_ACCESS=1"
set "MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_CLASS_LOOKUP=1"
if not defined OPENROUTER_MODEL_VISION set "OPENROUTER_MODEL_VISION=meta-llama/llama-3.2-11b-vision-instruct:free"
set "EDITING_VERIFY_PORT=8767"
set "OPENROUTER_SSL_VERIFY=0"

set "LOG=%REPO_ROOT%\reports\editing\quick_module_checks_%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%.log"
set "LOG=%LOG: =0%"

if not exist "%REPO_ROOT%\reports\editing" mkdir "%REPO_ROOT%\reports\editing"

echo Quick module checks device=%DEVICE% only=%ONLY% > "%LOG%"
echo Started: %DATE% %TIME% >> "%LOG%"
echo. >> "%LOG%"

py -3 "scripts\ensure_editing_verify_server.py"

call :maybe "Q1"  "ED_Q1 - Frames module quick check.yaml"
call :maybe "Q2"  "ED_Q2 - Stickers module quick check.yaml"
call :maybe "Q3"  "ED_Q3 - Crop module quick check.yaml"
call :maybe "Q4"  "ED_Q4 - Rotate module quick check.yaml"
call :maybe "Q5"  "ED_Q5 - Flip module quick check.yaml"
call :maybe "Q6"  "ED_Q6 - Brightness module quick check.yaml"
call :maybe "Q7"  "ED_Q7 - Temperature module quick check.yaml"
call :maybe "Q8"  "ED_Q8 - Adjust module quick check.yaml"
call :maybe "Q9"  "ED_Q9 - Text module quick check.yaml"
call :maybe "Q10" "ED_Q10 - Paint module quick check.yaml"
call :maybe "Q11" "ED_Q11 - Blur module quick check.yaml"

echo. >> "%LOG%"
echo Finished: %DATE% %TIME% >> "%LOG%"
type "%LOG%"

set "FAIL=0"
findstr /C:": FAIL" "%LOG%" >nul && set "FAIL=1"
exit /b %FAIL%

:maybe
if not "%ONLY%"=="" if /I not "%ONLY%"=="%~1" exit /b 0
call :run_maestro "%~2"
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
