@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Optional %1 = Maestro launcher (MAESTRO_CMD): bare name or full path to maestro.bat / maestro.cmd
REM MAESTRO_JAVA_HOME = optional JDK for Maestro (set by Jenkins when JAVA_HOME_OVERRIDE is used).
REM Do not inherit machine JAVA_HOME alone — agents often have JRE 8; Maestro needs JDK 17+.

REM --- Java (Maestro needs JDK 17+). Resolution order:
REM   1) MAESTRO_JAVA_HOME / Jenkins JAVA_HOME_OVERRIDE
REM   2) Existing JAVA_HOME when java.exe exists
REM   3) Common Adoptium / JetBrains install paths on the agent
REM   4) First java.exe from PATH (where java)
if not "%MAESTRO_JAVA_HOME%"=="" (
  if exist "%MAESTRO_JAVA_HOME%\bin\java.exe" (
    set "JAVA_HOME=%MAESTRO_JAVA_HOME%"
    goto :java_ok
  )
)
if not "%JAVA_HOME%"=="" (
  if exist "%JAVA_HOME%\bin\java.exe" goto :java_ok
)
for /d %%D in ("C:\Program Files\Eclipse Adoptium\jdk-17*") do (
  if exist "%%D\bin\java.exe" (
    set "JAVA_HOME=%%D"
    goto :java_ok
  )
)
for /d %%D in ("%USERPROFILE%\.jdks\jbr-17*") do (
  if exist "%%D\bin\java.exe" (
    set "JAVA_HOME=%%D"
    goto :java_ok
  )
)
for /d %%D in ("C:\Program Files\Eclipse Adoptium\jdk-21*") do (
  if exist "%%D\bin\java.exe" (
    set "JAVA_HOME=%%D"
    goto :java_ok
  )
)
for /d %%D in ("%USERPROFILE%\.jdks\jbr-21*") do (
  if exist "%%D\bin\java.exe" (
    set "JAVA_HOME=%%D"
    goto :java_ok
  )
)
for /d %%D in ("C:\Program Files\Eclipse Adoptium\jdk-25*") do (
  if exist "%%D\bin\java.exe" (
    set "JAVA_HOME=%%D"
    goto :java_ok
  )
)
for /f "delims=" %%W in ('where java 2^>nul') do (
  for %%P in ("%%~dpW..") do (
    if exist "%%~fP\bin\java.exe" (
      set "JAVA_HOME=%%~fP"
      goto :java_ok
    )
  )
)
echo ERROR: Java 17+ not found. Install Temurin JDK 17/21 or set MAESTRO_JAVA_HOME / JAVA_HOME_OVERRIDE.
endlocal & exit /b 1

:java_ok
if not exist "%JAVA_HOME%\bin\java.exe" (
  echo ERROR: Java not found at "%JAVA_HOME%"
  endlocal & exit /b 1
)

REM --- Maestro: directory that contains maestro.bat or maestro.cmd ---
REM Prefer ATP_MAESTRO_PARALLEL_HOME over MAESTRO_HOME when both are set (Jenkins parallel install).
if not "%ATP_MAESTRO_PARALLEL_HOME%"=="" (
  if exist "%ATP_MAESTRO_PARALLEL_HOME%\maestro.bat" (
    set "MAESTRO_HOME=%ATP_MAESTRO_PARALLEL_HOME%"
    goto :maestro_ok
  )
  if exist "%ATP_MAESTRO_PARALLEL_HOME%\maestro.cmd" (
    set "MAESTRO_HOME=%ATP_MAESTRO_PARALLEL_HOME%"
    goto :maestro_ok
  )
)

if not "%MAESTRO_HOME%"=="" (
  if exist "%MAESTRO_HOME%\maestro.bat" goto :maestro_ok
  if exist "%MAESTRO_HOME%\maestro.cmd" goto :maestro_ok
)

if not "%~1"=="" (
  if exist "%~f1" (
    for %%F in ("%~f1") do set "MAESTRO_HOME=%%~dpF"
    set "MAESTRO_HOME=!MAESTRO_HOME:~0,-1!"
    if exist "!MAESTRO_HOME!\maestro.bat" goto :maestro_ok
    if exist "!MAESTRO_HOME!\maestro.cmd" goto :maestro_ok
  )
)

set "MAESTRO_HOME=%USERPROFILE%\maestro\maestro\bin"
if exist "%MAESTRO_HOME%\maestro.bat" goto :maestro_ok
if exist "%MAESTRO_HOME%\maestro.cmd" goto :maestro_ok

for /f "delims=" %%W in ('where maestro.bat 2^>nul') do (
  for %%P in ("%%~dpW.") do set "MAESTRO_HOME=%%~fP"
  goto :maestro_ok
)
for /f "delims=" %%W in ('where maestro.cmd 2^>nul') do (
  for %%P in ("%%~dpW.") do set "MAESTRO_HOME=%%~fP"
  goto :maestro_ok
)

if not "%~1"=="" (
  for /f "delims=" %%W in ('where "%~1" 2^>nul') do (
    for %%P in ("%%~dpW.") do set "MAESTRO_HOME=%%~fP"
    goto :maestro_ok
  )
)

echo ERROR: Maestro not found.
echo Set MAESTRO_HOME to the folder that contains maestro.bat, add Maestro to machine PATH,
echo or set the job parameter MAESTRO_CMD to the full path of maestro.bat.
echo When Jenkins runs as Local System, %%USERPROFILE%% is systemprofile — the default user install path does not apply.
endlocal & exit /b 1

:maestro_ok
set "PATH=%JAVA_HOME%\bin;%MAESTRO_HOME%;%PATH%"

REM --- ADB: Jenkins Local System has no user PATH — set ANDROID_HOME in the job or rely on fallbacks below ---
set "ADB_HOME="
if defined ANDROID_HOME if exist "%ANDROID_HOME%\platform-tools\adb.exe" set "ADB_HOME=%ANDROID_HOME%\platform-tools"
if not defined ADB_HOME if defined ANDROID_SDK_ROOT if exist "%ANDROID_SDK_ROOT%\platform-tools\adb.exe" set "ADB_HOME=%ANDROID_SDK_ROOT%\platform-tools"
if not defined ADB_HOME if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" set "ADB_HOME=%LOCALAPPDATA%\Android\Sdk\platform-tools"
if not defined ADB_HOME if exist "%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe" set "ADB_HOME=%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools"
if not defined ADB_HOME (
  for /f "delims=" %%W in ('where adb 2^>nul') do (
    for %%P in ("%%~dpW.") do set "ADB_HOME=%%~fP"
    goto :adb_ok
  )
)
:adb_ok
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
