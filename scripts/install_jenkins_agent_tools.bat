@echo off
setlocal EnableExtensions
REM Copy wipe/cleanup scripts to %%JENKINS_HOME%%\kodak-atp-tools (survives workspace wipes).
if "%JENKINS_HOME%"=="" (
  echo [agent-tools] WARN: JENKINS_HOME not set; skipping tool install
  exit /b 0
)
set "DEST=%JENKINS_HOME%\kodak-atp-tools"
if not exist "%DEST%" mkdir "%DEST%" 2>nul
set "SRC=%~dp0"
echo [agent-tools] Installing to "%DEST%"
copy /Y "%SRC%wipe_jenkins_workspace.ps1" "%DEST%\" >nul 2>&1
copy /Y "%SRC%jenkins_ci_wipe_workspace.bat" "%DEST%\" >nul 2>&1
copy /Y "%SRC%release_jenkins_workspace_locks.ps1" "%DEST%\" >nul 2>&1
copy /Y "%SRC%jenkins_ci_release_workspace.bat" "%DEST%\" >nul 2>&1
copy /Y "%SRC%cleanup_temp_maestro_apks.ps1" "%DEST%\" >nul 2>&1
echo [agent-tools] Done
exit /b 0
