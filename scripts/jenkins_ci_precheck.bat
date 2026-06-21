@echo off
setlocal EnableExtensions
REM Jenkins precheck: Java, ADB, Maestro (version via "maestro version" / "--version"), YAML.
REM Does not fail on "maestro --help" exit codes (some CLI builds return 1).
if "%~1"=="" (
  echo ERROR: workspace required
  exit /b 1
)
cd /d "%~1"
echo [precheck] workspace=%CD%
echo [precheck] MAESTRO_CMD=%~2
if defined ATP_MAESTRO_PARALLEL_HOME echo [precheck] ATP_MAESTRO_PARALLEL_HOME=%ATP_MAESTRO_PARALLEL_HOME%
if defined MAESTRO_HOME echo [precheck] MAESTRO_HOME=%MAESTRO_HOME%
echo =====================================
echo PRECHECK JAVA ^(quick^)
echo =====================================
where java
java -version
if errorlevel 1 (
  echo 1> "precheck_failed.flag"
  echo 1> "pipeline_failed.flag"
  exit /b 1
)
call "%~dp0precheck_environment.bat" "%~2" "%~3" || (
  echo 1> "precheck_failed.flag"
  echo 1> "pipeline_failed.flag"
  exit /b 1
)
exit /b 0
