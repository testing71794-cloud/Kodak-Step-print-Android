@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if exist "build-summary\ai_status.txt" findstr /C:"AI_STATUS=AVAILABLE" "build-summary\ai_status.txt" >nul && set "EXCEL_AI_OPENROUTER=1" || set "EXCEL_AI_OPENROUTER=0"
echo === Intelligent platform (EXCEL_AI_OPENROUTER=%EXCEL_AI_OPENROUTER%) ===
if not defined PYTHON_EXE (
  where python >nul 2>&1 || (
    echo python not on PATH — cannot run intelligent platform.
    exit /b 1
  )
  set "PYTHON_EXE=python"
)

echo [DEBUG] "%PYTHON_EXE%" -m intelligent_platform
"%PYTHON_EXE%" -m intelligent_platform
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo intelligent platform exited with %ERR%
  exit /b %ERR%
)
echo Done.
exit /b 0
