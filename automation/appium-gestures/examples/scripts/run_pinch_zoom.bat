@echo off
setlocal EnableExtensions
REM Optional Maestro hook — COPY to your flows folder if you choose Option A.
REM Does NOT run unless you add runScript to a flow yourself.
REM Windows Jenkins agent / local device node.

set "MODULE_DIR=%~dp0..\.."
if not exist "%MODULE_DIR%\pom.xml" (
  echo ERROR: appium-gestures module not found at %MODULE_DIR%
  exit /b 1
)

set "GESTURE=both"
set "UDID="
if not "%~1"=="" set "GESTURE=%~1"
if not "%~2"=="" set "UDID=%~2"

cd /d "%MODULE_DIR%"
if not defined JAVA_HOME (
  for /f "delims=" %%J in ('where java 2^>nul') do set "JAVA_HOME=%%~dpJ.." & goto :java_ok
)
:java_ok

set "MVN_ARGS=-q exec:java"
where mvn >nul 2>&1
if errorlevel 1 (
  if exist "%MODULE_DIR%\target\appium-gestures-1.0.0.jar" (
    if defined UDID (
      "%JAVA_HOME%\bin\java.exe" -jar "%MODULE_DIR%\target\appium-gestures-1.0.0.jar" %GESTURE% --udid %UDID%
    ) else (
      "%JAVA_HOME%\bin\java.exe" -jar "%MODULE_DIR%\target\appium-gestures-1.0.0.jar" %GESTURE%
    )
    goto :pinch_done
  )
  echo ERROR: mvn not on PATH and target\appium-gestures-1.0.0.jar missing. Run: mvn package
  exit /b 1
)
if defined UDID (
  call mvn %MVN_ARGS% "-Dexec.args=%GESTURE% --udid %UDID%"
) else (
  call mvn %MVN_ARGS% "-Dexec.args=%GESTURE%"
)
:pinch_done
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo ERROR: Pinch gesture failed exit=%RC%
  exit /b %RC%
)
echo Pinch gesture OK
exit /b 0
