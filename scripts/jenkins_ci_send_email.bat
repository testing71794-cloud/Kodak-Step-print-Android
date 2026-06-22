@echo off
setlocal EnableExtensions
if "%~1"=="" (
  echo ERROR: workspace required
  exit /b 1
)
cd /d "%~1"
set "WS_ROOT=%~1"
if defined BRANCH_NAME if not defined ATP_GIT_BRANCH set "ATP_GIT_BRANCH=%BRANCH_NAME%"
if defined GIT_BRANCH if not defined ATP_GIT_BRANCH set "ATP_GIT_BRANCH=%GIT_BRANCH%"
if defined BUILD_URL echo [gcp-email] BUILD_URL=%BUILD_URL%
if defined BUILD_NUMBER echo [gcp-email] BUILD_NUMBER=%BUILD_NUMBER%
if exist "%WS_ROOT%\build-summary\failed_tests_artifacts.zip" (
  for %%A in ("%WS_ROOT%\build-summary\failed_tests_artifacts.zip") do echo [gcp-email] ZIP Size: %%~zA bytes
)
pushd "%~dp0"
call "%~dp0jenkins_resolve_python.bat"
if errorlevel 1 (
  popd
  echo 1> "%WS_ROOT%\email_failed.flag"
  exit /b 1
)
echo Running send_email with Jenkins credential gmail-smtp-kodak ...
echo [DEBUG] "%PYTHON_EXE%" "%~dp0..\mailout\send_email.py"
"%PYTHON_EXE%" "%~dp0..\mailout\send_email.py" || (
  echo 1> "%WS_ROOT%\email_failed.flag"
  popd
  exit /b 1
)
popd
exit /b 0
