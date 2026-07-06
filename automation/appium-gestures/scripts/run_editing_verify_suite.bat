@echo off

setlocal EnableExtensions EnableDelayedExpansion

REM Enterprise editing suite: ED_01-ED_12 + ED_99 master E2E with in-flow OpenRouter AI.

REM Usage: run_editing_verify_suite.bat [DEVICE_SERIAL]



set "DEVICE=%~1"

if "%DEVICE%"=="" set "DEVICE=ZA222RFQ75"

set "REPO_ROOT=%~dp0..\..\.."

cd /d "%REPO_ROOT%"



set "MAESTRO_BIN=C:\Tools\maestro-parallel\bin\maestro.bat"

if defined OPENROUTER_API_KEY if not defined OpenRouterAPI set "OpenRouterAPI=%OPENROUTER_API_KEY%"

set "MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_ACCESS=1"

set "MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_CLASS_LOOKUP=1"

if not defined OPENROUTER_MODEL_VISION set "OPENROUTER_MODEL_VISION=meta-llama/llama-3.2-11b-vision-instruct:free"



set "LOG=%REPO_ROOT%\reports\editing\verify_suite_%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%.log"

set "LOG=%LOG: =0%"



if not exist "%REPO_ROOT%\reports\editing" mkdir "%REPO_ROOT%\reports\editing"



echo Editing enterprise suite device=%DEVICE% > "%LOG%"

echo GraalJS host access=%MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_ACCESS% >> "%LOG%"

echo Started: %DATE% %TIME% >> "%LOG%"

echo. >> "%LOG%"



call :run_maestro "ED_01 - Enter edit photo mode.yaml"

call :run_maestro "ED_02 - Apply filter to photo.yaml"

call :run_maestro "ED_03 - Frames comprehensive.yaml"

call :run_maestro "ED_04 - Stickers comprehensive.yaml"

call :run_maestro "ED_05 - Crop comprehensive.yaml"

call :run_maestro "ED_06 - Rotate comprehensive.yaml"

call :run_maestro "ED_07 - Flip comprehensive.yaml"

call :run_maestro "ED_08 - Adjust comprehensive.yaml"

call :run_maestro "ED_09 - Text comprehensive.yaml"

call :run_maestro "ED_10 - Draw comprehensive.yaml"

call :run_maestro "ED_11 - Blur effects comprehensive.yaml"

call :run_maestro "ED_12 - Save comprehensive.yaml"

call :run_maestro "ED_99 - Master edit module E2E.yaml"



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

