@echo off
setlocal EnableExtensions EnableDelayedExpansion
goto :script_body

REM Sleep without timeout.exe (Jenkins non-TTY safe).
:sleep_seconds
set /a "_ss=%~1"
if !_ss! LSS 1 set "_ss=1"
if !_ss! GTR 120 set "_ss=120"
set /a "_ss_ping=!_ss!+1"
ping 127.0.0.1 -n !_ss_ping! >nul
exit /b 0

:script_body
call "%~dp0set_maestro_java.bat" || exit /b 1

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
set "OUT_FILE=%REPO_ROOT%\detected_devices.txt"
set "ADB_EXE="
if defined ADB_HOME if exist "%ADB_HOME%\adb.exe" set "ADB_EXE=%ADB_HOME%\adb.exe"
if not defined ADB_EXE if exist "C:\Users\HP\AppData\Local\Android\Sdk\platform-tools\adb.exe" set "ADB_EXE=C:\Users\HP\AppData\Local\Android\Sdk\platform-tools\adb.exe"
if not defined ADB_EXE (
    for /f "delims=" %%W in ('where adb 2^>nul') do (
        set "ADB_EXE=%%W"
        goto :adb_ok
    )
)
:adb_ok

if not defined ADB_DETECT_WAIT_ATTEMPTS set "ADB_DETECT_WAIT_ATTEMPTS=20"
if not defined ADB_DETECT_WAIT_SECS set "ADB_DETECT_WAIT_SECS=3"

echo =========================
echo Connected Android devices
echo =========================

if not defined ADB_EXE (
    echo ERROR: adb.exe not found. Expected under ADB_HOME or Android SDK platform-tools.
    exit /b 1
)
echo %ADB_EXE%

del /q "%OUT_FILE%" 2>nul

set /a "_ATT=0"
:detect_loop
set /a "_ATT+=1"
echo.
echo [detect] attempt !_ATT!/%ADB_DETECT_WAIT_ATTEMPTS% ^(wait %ADB_DETECT_WAIT_SECS%s between retries^)

if !_ATT! GTR 1 (
    echo [detect] restarting ADB server...
    "%ADB_EXE%" kill-server >nul 2>&1
    call :sleep_seconds 2
)

echo Starting ADB server...
"%ADB_EXE%" start-server >nul 2>&1 || (
    echo ERROR: failed to start adb server. Check USB/debug permissions and Android SDK path.
    exit /b 1
)

echo.
echo --- adb devices ^(full output^) ---
"%ADB_EXE%" devices
echo --- end adb devices ---

(
for /f "skip=1 tokens=1,2" %%A in ('"%ADB_EXE%" devices 2^>nul') do (
    if /I "%%B"=="device" echo %%A
)
) > "%OUT_FILE%"

set /a COUNT=0
for /f "usebackq delims=" %%A in ("%OUT_FILE%") do set /a COUNT+=1

if !COUNT! GTR 0 goto :detect_done

if !_ATT! LSS %ADB_DETECT_WAIT_ATTEMPTS% (
    echo [WARN] No device in state "device" yet; waiting %ADB_DETECT_WAIT_SECS%s...
    echo [hint] Unlock phone, enable USB debugging, accept RSA prompt, try another USB port/cable.
    call :sleep_seconds %ADB_DETECT_WAIT_SECS%
    goto :detect_loop
)

echo.
echo Devices detected: 0
echo Device list saved to: "%OUT_FILE%"
echo ERROR: No authorized Android devices found ^(state "device"^). Unauthorized/offline/recovery/sideload are excluded.
echo.
echo Troubleshooting:
echo   1. On the phone: Developer options - USB debugging ON; unlock screen.
echo   2. If you see "Allow USB debugging?" tap Allow ^(and Always allow this computer^).
echo   3. Run as the same Windows user that owns the USB session ^(Jenkins agent vs interactive login^).
echo   4. In a CMD window on this PC: "%ADB_EXE%" devices   ^(must show SERIAL    device^)
echo   5. Replug USB; avoid hubs; set USB mode to File transfer / MTP if needed.
echo   6. Override wait: set ADB_DETECT_WAIT_ATTEMPTS=40 and ADB_DETECT_WAIT_SECS=5
exit /b 1

:detect_done
echo.
echo Devices detected: !COUNT!
echo Device list saved to: "%OUT_FILE%"
type "%OUT_FILE%"
exit /b 0
