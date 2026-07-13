@echo off
setlocal EnableExtensions
REM Safe replacement for Jenkins deleteDir() on Windows (handles locked Maestro/Java files).
REM Usage: jenkins_ci_wipe_workspace.bat "C:\Jenkins\ws\kodak-atp-android" [Full^|ReleaseOnly]
if "%~1"=="" (
  echo ERROR: %~nx0 requires workspace path as first argument.
  exit /b 1
)
set "WS=%~1"
set "MODE=%~2"
if /I not "%MODE%"=="ReleaseOnly" set "MODE=Full"
echo === WIPE JENKINS WORKSPACE (%MODE%) ===
if not exist "%WS%" (
  mkdir "%WS%" 2>nul
)
set "PS1=%~dp0wipe_jenkins_workspace.ps1"
if not exist "%PS1%" set "PS1=%~dp0..\scripts\wipe_jenkins_workspace.ps1"
if not exist "%PS1%" (
  if exist "%JENKINS_HOME%\kodak-atp-tools\wipe_jenkins_workspace.ps1" (
    set "PS1=%JENKINS_HOME%\kodak-atp-tools\wipe_jenkins_workspace.ps1"
  )
)
if not exist "%PS1%" (
  echo [wipe-ws] WARN: wipe_jenkins_workspace.ps1 not found; using bootstrap robocopy mirror
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws='%WS%'; if (-not (Test-Path -LiteralPath $ws)) { New-Item -ItemType Directory -Path $ws -Force | Out-Null }; Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.CommandLine -and ($_.CommandLine -like ('*'+$ws+'*') -or $_.CommandLine -match '(?i)maestro|jenkins_atp_stage|run_one_flow') -and $_.Name -match '^(java|python|node|cmd)\.exe$' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }; Start-Sleep -Seconds 2; $e=Join-Path $env:TEMP ('je'+[guid]::NewGuid().ToString('n')); New-Item -ItemType Directory -Path $e -Force | Out-Null; cmd /c \"attrib -R `\"$ws\\*`\" /S /D >nul 2>&1\"; robocopy $e $ws /MIR /R:3 /W:3 /NFL /NDL /NJH /NJS /NP | Out-Null; Remove-Item $e -Recurse -Force -EA SilentlyContinue"
  if /I "%MODE%"=="Full" exit /b 0
  exit /b 0
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Workspace "%WS%" -Mode %MODE%
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo [wipe-ws] WARN: wipe exited %EC% (continuing pipeline)
  exit /b 0
)
exit /b 0
