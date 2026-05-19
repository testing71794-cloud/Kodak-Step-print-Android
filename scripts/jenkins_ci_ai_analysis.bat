@echo off
setlocal EnableExtensions
if "%~1"=="" (
  echo ERROR: workspace required
  exit /b 1
)
cd /d "%~1"
set "WS_ROOT=%~1"
if not exist "%WS_ROOT%\build-summary" mkdir "%WS_ROOT%\build-summary"
if not exist "%WS_ROOT%\build-summary\ai_status.txt" (
  echo AI_STATUS=FILE_MISSING > "%WS_ROOT%\build-summary\ai_status.txt"
)
pushd "%~dp0"
call "%~dp0jenkins_resolve_python.bat"
if errorlevel 1 (
  popd
  echo 1> "%WS_ROOT%\ai_failed.flag"
  exit /b 1
)
echo [DEBUG] "%PYTHON_EXE%" "%~dp0run_ai_analysis.bat"
call "%~dp0run_ai_analysis.bat" || (
  echo 1> "%WS_ROOT%\ai_failed.flag"
  popd
  exit /b 1
)
popd
exit /b 0
