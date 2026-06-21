@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM script_rev=2026-06-maestro-version-precheck-1

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%set_maestro_java.bat" "%~1" || exit /b 1

if defined JAVA_HOME set "PATH=%JAVA_HOME%\bin;%PATH%"
if defined MAESTRO_HOME set "PATH=%MAESTRO_HOME%;%PATH%"
if defined ATP_MAESTRO_PARALLEL_HOME set "PATH=%ATP_MAESTRO_PARALLEL_HOME%;%PATH%"
if defined ADB_HOME set "PATH=%ADB_HOME%;%PATH%"

set "ADB_EXE="
if defined ADB_HOME if exist "%ADB_HOME%\adb.exe" set "ADB_EXE=%ADB_HOME%\adb.exe"
if not defined ADB_EXE (
  for /f "delims=" %%W in ('where adb 2^>nul') do (
    set "ADB_EXE=%%W"
    goto :adb_resolved
  )
)
:adb_resolved

set "MAESTRO_BIN="
set "MAESTRO_RESOLVED_HOME=%MAESTRO_HOME%"
if defined ATP_MAESTRO_PARALLEL_HOME (
  if exist "%ATP_MAESTRO_PARALLEL_HOME%\maestro.bat" (
    set "MAESTRO_RESOLVED_HOME=%ATP_MAESTRO_PARALLEL_HOME%"
    set "MAESTRO_BIN=%ATP_MAESTRO_PARALLEL_HOME%\maestro.bat"
  ) else if exist "%ATP_MAESTRO_PARALLEL_HOME%\maestro.cmd" (
    set "MAESTRO_RESOLVED_HOME=%ATP_MAESTRO_PARALLEL_HOME%"
    set "MAESTRO_BIN=%ATP_MAESTRO_PARALLEL_HOME%\maestro.cmd"
  )
)
if not defined MAESTRO_BIN if defined MAESTRO_HOME (
  if exist "%MAESTRO_HOME%\maestro.bat" set "MAESTRO_BIN=%MAESTRO_HOME%\maestro.bat"
  if not defined MAESTRO_BIN if exist "%MAESTRO_HOME%\maestro.cmd" set "MAESTRO_BIN=%MAESTRO_HOME%\maestro.cmd"
)

echo =====================================
echo PRECHECK JAVA
echo =====================================
echo [DEBUG] JAVA_HOME=%JAVA_HOME%
echo [DEBUG] MAESTRO_HOME=%MAESTRO_HOME%
if defined ATP_MAESTRO_PARALLEL_HOME echo [DEBUG] ATP_MAESTRO_PARALLEL_HOME=%ATP_MAESTRO_PARALLEL_HOME%
if defined ADB_HOME echo [DEBUG] ADB_HOME=%ADB_HOME%
if defined ADB_EXE echo [DEBUG] ADB_EXE=%ADB_EXE%
if defined MAESTRO_RESOLVED_HOME echo [DEBUG] MAESTRO_RESOLVED_HOME=%MAESTRO_RESOLVED_HOME%
if defined MAESTRO_BIN echo [DEBUG] MAESTRO_BIN=%MAESTRO_BIN%
where java
"%JAVA_HOME%\bin\java.exe" -version
if errorlevel 1 exit /b 1
echo =====================================

echo Checking ADB...
if not defined ADB_EXE (
  echo ERROR: adb.exe not found
  exit /b 1
)
echo [DEBUG] "%ADB_EXE%" start-server
"%ADB_EXE%" start-server >nul 2>&1
echo [DEBUG] "%ADB_EXE%" devices
"%ADB_EXE%" devices
if errorlevel 1 exit /b 1
echo =====================================

echo Checking Maestro...
if not defined MAESTRO_BIN (
  echo ERROR: maestro.bat not found under MAESTRO_HOME or ATP_MAESTRO_PARALLEL_HOME
  exit /b 1
)
echo [INFO] Resolved Maestro path: %MAESTRO_BIN%
echo [INFO] Resolved Maestro home: %MAESTRO_RESOLVED_HOME%

set "MAESTRO_VERSION="
set "MAESTRO_VERSION_FILE=%TEMP%\atp_maestro_version_%RANDOM%_%RANDOM%.txt"

echo [DEBUG] call "%MAESTRO_BIN%" version
call "%MAESTRO_BIN%" version > "%MAESTRO_VERSION_FILE%" 2>&1
set "MAESTRO_VERSION_RC=!ERRORLEVEL!"
if !MAESTRO_VERSION_RC! equ 0 goto :maestro_version_ok

echo [DEBUG] call "%MAESTRO_BIN%" --version ^(fallback for Maestro 2.2.x / 2.5.x^)
call "%MAESTRO_BIN%" --version > "%MAESTRO_VERSION_FILE%" 2>&1
set "MAESTRO_VERSION_RC=!ERRORLEVEL!"
if !MAESTRO_VERSION_RC! neq 0 (
  echo ERROR: Maestro version check failed ^(tried "version" and "--version"^)
  type "%MAESTRO_VERSION_FILE%"
  del "%MAESTRO_VERSION_FILE%" 2>nul
  exit /b 1
)

:maestro_version_ok
set "MAESTRO_VERSION="
for /f "usebackq delims=" %%L in (`findstr /R /C:"^[0-9][0-9]*\.[0-9]" "%MAESTRO_VERSION_FILE%" 2^>nul`) do (
  set "MAESTRO_VERSION=%%L"
  goto :maestro_version_parsed
)
:maestro_version_parsed
if not defined MAESTRO_VERSION set /p MAESTRO_VERSION=<"%MAESTRO_VERSION_FILE%"
del "%MAESTRO_VERSION_FILE%" 2>nul
if not defined MAESTRO_VERSION (
  echo ERROR: Maestro version output was empty
  exit /b 1
)
echo [INFO] Maestro version: !MAESTRO_VERSION!
echo =====================================

echo Validating Maestro YAML (ATP TestCase Flows)...
set "REPO_ROOT=%CD%"
for %%P in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fP"
python "%SCRIPT_DIR%validate_maestro_yaml.py" "%REPO_ROOT%\ATP TestCase Flows"
if errorlevel 1 (
  echo ERROR: Maestro YAML validation failed
  exit /b 1
)
echo Maestro YAML validation OK
echo =====================================

echo Precheck complete
exit /b 0
