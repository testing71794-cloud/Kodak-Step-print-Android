@echo off
setlocal EnableExtensions
REM Release locks only (post-build / legacy path migration).
if "%~1"=="" exit /b 0
set "WS=%~1"
if not exist "%WS%" exit /b 0
echo === RELEASE WORKSPACE LOCKS ===
if exist "%JENKINS_HOME%\kodak-atp-tools\jenkins_ci_wipe_workspace.bat" (
  call "%JENKINS_HOME%\kodak-atp-tools\jenkins_ci_wipe_workspace.bat" "%WS%" ReleaseOnly
  exit /b 0
)
if exist "%~dp0jenkins_ci_wipe_workspace.bat" (
  call "%~dp0jenkins_ci_wipe_workspace.bat" "%WS%" ReleaseOnly
  exit /b 0
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wipe_jenkins_workspace.ps1" -Workspace "%WS%" -Mode ReleaseOnly
exit /b 0
