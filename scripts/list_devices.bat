@echo off
REM Delegates to scripts\windows_agent\list_devices.bat (quoted paths for Jenkins workspaces with spaces).
call "%~dp0windows_agent\list_devices.bat" %*
exit /b %ERRORLEVEL%
