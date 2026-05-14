@echo off
setlocal EnableExtensions
REM ATP TestCase Flows runner (recursive yaml/yml). Does not replace Printing / Non-printing runners.
REM Args: APP_PACKAGE CLEAR_STATE MAESTRO_CMD [ATP_SUBFOLDER]
REM       Optional 4th arg runs only that child folder under "ATP TestCase Flows" (e.g. Camera, SignUp_Login).

set "RR=%~dp0.."
for %%I in ("%RR%") do set "RR=%%~fI"

cd /d "%RR%"
if "%~4"=="" (
  python -m execution.atp_jenkins_orchestrator "%RR%" "%~1" "%~2" "%~3" ""
) else (
  python -m execution.atp_jenkins_orchestrator "%RR%" "%~1" "%~2" "%~3" "%~4"
)
set "EC=%ERRORLEVEL%"
endlocal
exit /b %EC%
