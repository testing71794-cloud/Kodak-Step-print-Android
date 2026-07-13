@echo off
setlocal EnableExtensions
REM One-time setup on the Windows Jenkins agent (run from repo root as Jenkins user).
REM Installs wipe scripts to %%JENKINS_HOME%%\kodak-atp-tools so builds work before first unstash.
cd /d "%~dp0.."
if "%JENKINS_HOME%"=="" (
  echo ERROR: JENKINS_HOME is not set. Run this from the Jenkins agent user session.
  exit /b 1
)
call scripts\install_jenkins_agent_tools.bat
echo.
echo Installed agent tools to "%JENKINS_HOME%\kodak-atp-tools"
echo Optional: wipe legacy workspace now:
echo   call "%JENKINS_HOME%\kodak-atp-tools\jenkins_ci_wipe_workspace.bat" "C:\Jenkins\workspace\Kodak Step Print Android" Full
exit /b 0
