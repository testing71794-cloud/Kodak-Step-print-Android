@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Optional %1 = Maestro launcher (MAESTRO_CMD): bare name or full path to maestro.bat / maestro.cmd
REM MAESTRO_JAVA_HOME = optional JDK for Maestro (set by Jenkins when JAVA_HOME_OVERRIDE is used).

call :resolve_java || exit /b 1
call :resolve_maestro "%~1" || exit /b 1
call :resolve_adb

set "PATH=%JAVA_HOME%\bin;%MAESTRO_HOME%;%PATH%"
if defined ADB_HOME set "PATH=%ADB_HOME%;%PATH%"

echo JAVA_HOME=%JAVA_HOME%
echo MAESTRO_HOME=%MAESTRO_HOME%
if defined ATP_MAESTRO_PARALLEL_HOME echo ATP_MAESTRO_PARALLEL_HOME=%ATP_MAESTRO_PARALLEL_HOME%
if defined ADB_HOME echo ADB_HOME=%ADB_HOME%

endlocal & (
  set "JAVA_HOME=%JAVA_HOME%"
  set "MAESTRO_HOME=%MAESTRO_HOME%"
  set "ADB_HOME=%ADB_HOME%"
  set "PATH=%PATH%"
)
exit /b 0

:resolve_java
if not "%MAESTRO_JAVA_HOME%"=="" if exist "%MAESTRO_JAVA_HOME%\bin\java.exe" set "JAVA_HOME=%MAESTRO_JAVA_HOME%" & exit /b 0
if not "%JAVA_HOME%"=="" if exist "%JAVA_HOME%\bin\java.exe" exit /b 0
for /d %%D in ("C:\Program Files\Eclipse Adoptium\jdk-17*") do if exist "%%D\bin\java.exe" set "JAVA_HOME=%%D" & exit /b 0
for /d %%D in ("%USERPROFILE%\.jdks\jbr-17*") do if exist "%%D\bin\java.exe" set "JAVA_HOME=%%D" & exit /b 0
for /d %%D in ("C:\Program Files\Eclipse Adoptium\jdk-21*") do if exist "%%D\bin\java.exe" set "JAVA_HOME=%%D" & exit /b 0
for /d %%D in ("%USERPROFILE%\.jdks\jbr-21*") do if exist "%%D\bin\java.exe" set "JAVA_HOME=%%D" & exit /b 0
for /d %%D in ("C:\Program Files\Eclipse Adoptium\jdk-25*") do if exist "%%D\bin\java.exe" set "JAVA_HOME=%%D" & exit /b 0
for /f "delims=" %%W in ('where java 2^>nul') do for %%P in ("%%~dpW..") do if exist "%%~fP\bin\java.exe" set "JAVA_HOME=%%~fP" & exit /b 0
echo ERROR: Java 17+ not found. Install Temurin JDK 17/21 or set MAESTRO_JAVA_HOME / JAVA_HOME_OVERRIDE.
exit /b 1

:resolve_maestro
set "MAESTRO_CMD_ARG=%~1"
if not "%ATP_MAESTRO_PARALLEL_HOME%"=="" call :try_maestro_home "%ATP_MAESTRO_PARALLEL_HOME%" && exit /b 0
if exist "C:\Tools\maestro-parallel\bin\maestro.bat" set "ATP_MAESTRO_PARALLEL_HOME=C:\Tools\maestro-parallel\bin" & call :try_maestro_home "C:\Tools\maestro-parallel\bin" && exit /b 0
if exist "C:\Tools\maestro-parallel\bin\maestro.cmd" set "ATP_MAESTRO_PARALLEL_HOME=C:\Tools\maestro-parallel\bin" & call :try_maestro_home "C:\Tools\maestro-parallel\bin" && exit /b 0
if not "%MAESTRO_HOME%"=="" call :try_maestro_home "%MAESTRO_HOME%" && exit /b 0
if not "%MAESTRO_CMD_ARG%"=="" if exist "%MAESTRO_CMD_ARG%" for %%F in ("%MAESTRO_CMD_ARG%") do set "MAESTRO_HOME=%%~dpF" & set "MAESTRO_HOME=!MAESTRO_HOME:~0,-1!" & call :try_maestro_home "!MAESTRO_HOME!" && exit /b 0
set "MAESTRO_HOME=%USERPROFILE%\maestro\maestro\bin"
call :try_maestro_home "%MAESTRO_HOME%" && exit /b 0
for /f "delims=" %%W in ('where maestro.bat 2^>nul') do for %%P in ("%%~dpW.") do set "MAESTRO_HOME=%%~fP" & exit /b 0
for /f "delims=" %%W in ('where maestro.cmd 2^>nul') do for %%P in ("%%~dpW.") do set "MAESTRO_HOME=%%~fP" & exit /b 0
if not "%MAESTRO_CMD_ARG%"=="" for /f "delims=" %%W in ('where "%MAESTRO_CMD_ARG%" 2^>nul') do for %%P in ("%%~dpW.") do set "MAESTRO_HOME=%%~fP" & exit /b 0
echo ERROR: Maestro not found.
echo Set MAESTRO_HOME to the folder that contains maestro.bat, add Maestro to machine PATH,
echo or set the job parameter MAESTRO_CMD to the full path of maestro.bat.
exit /b 1

:try_maestro_home
if exist "%~1\maestro.bat" set "MAESTRO_HOME=%~1" & exit /b 0
if exist "%~1\maestro.cmd" set "MAESTRO_HOME=%~1" & exit /b 0
exit /b 1

:resolve_adb
set "ADB_HOME="
if defined ANDROID_HOME if exist "%ANDROID_HOME%\platform-tools\adb.exe" set "ADB_HOME=%ANDROID_HOME%\platform-tools" & exit /b 0
if defined ANDROID_SDK_ROOT if exist "%ANDROID_SDK_ROOT%\platform-tools\adb.exe" set "ADB_HOME=%ANDROID_SDK_ROOT%\platform-tools" & exit /b 0
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" set "ADB_HOME=%LOCALAPPDATA%\Android\Sdk\platform-tools" & exit /b 0
if exist "%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe" set "ADB_HOME=%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools" & exit /b 0
for /f "delims=" %%W in ('where adb 2^>nul') do for %%P in ("%%~dpW.") do set "ADB_HOME=%%~fP" & exit /b 0
exit /b 0
