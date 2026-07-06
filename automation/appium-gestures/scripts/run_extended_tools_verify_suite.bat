@echo off

setlocal EnableExtensions EnableDelayedExpansion

REM P0 extended-toolbar suite: Blur, Text, Paint (comprehensive + UI + combined) with OpenRouter AI.

REM Usage: run_extended_tools_verify_suite.bat [DEVICE_SERIAL]

set "DEVICE=%~1"
if "%DEVICE%"=="" set "DEVICE=ZA222RFQ75"

set "REPO_ROOT=%~dp0..\..\.."
cd /d "%REPO_ROOT%"

set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"
if defined OPENROUTER_API_KEY if not defined OpenRouterAPI set "OpenRouterAPI=%OPENROUTER_API_KEY%"
set "MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_ACCESS=1"
set "MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_CLASS_LOOKUP=1"
if not defined OPENROUTER_MODEL_VISION set "OPENROUTER_MODEL_VISION=meta-llama/llama-3.2-11b-vision-instruct:free"
set "EDITING_VERIFY_PORT=8767"
set "OPENROUTER_SSL_VERIFY=0"

set "LOG=%REPO_ROOT%\reports\editing\extended_tools_verify_%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%.log"
set "LOG=%LOG: =0%"

if not exist "%REPO_ROOT%\reports\editing" mkdir "%REPO_ROOT%\reports\editing"

echo Extended tools P0 suite device=%DEVICE% > "%LOG%"
echo Started: %DATE% %TIME% >> "%LOG%"
echo. >> "%LOG%"

py -3 "scripts\ensure_editing_verify_server.py"
if errorlevel 1 (
  echo WARN: verify server may not be ready >> "%LOG%"
)

call :run_maestro "ED_11A - Blur comprehensive with AI.yaml"
call :run_maestro "ED_11B - Blur screen navigation and UI.yaml"
call :run_maestro "ED_09A - Text comprehensive with AI.yaml"
call :run_maestro "ED_09B - Text screen navigation and UI.yaml"
call :run_maestro "ED_10A - Paint comprehensive with AI.yaml"
call :run_maestro "ED_10B - Paint screen navigation and UI.yaml"
call :run_maestro "ED_12B - Blur text paint combined with AI.yaml"

echo. >> "%LOG%"
echo Finished: %DATE% %TIME% >> "%LOG%"
type "%LOG%"

set "FAIL=0"
findstr /C:": FAIL" "%LOG%" >nul && set "FAIL=1"
exit /b %FAIL%

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
