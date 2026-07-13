#Requires -Version 5.1
<#
.SYNOPSIS
  Stop stale Maestro/orchestrator processes and trim generated dirs before Jenkins deleteDir().

  Prevents: jenkins.util.io.CompositeIOException: Unable to delete workspace
  when java/python from a prior build still hold handles under the job workspace.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Workspace,

    [int] $GraceSeconds = 2
)

$ErrorActionPreference = 'Continue'

function Write-ReleaseLog {
    param([string] $Message)
    Write-Host "[release-ws] $Message"
}

function Get-NormalizedPath {
    param([string] $Path)
    if (-not $Path) { return $null }
    try {
        return (Get-Item -LiteralPath $Path -ErrorAction Stop).FullName
    } catch {
        return $null
    }
}

function Test-ProcessUsesWorkspace {
    param(
        [string] $CommandLine,
        [string] $WorkspacePath
    )
    if (-not $CommandLine) { return $false }
    if ($CommandLine -like "*$WorkspacePath*") { return $true }
    return $false
}

function Remove-DirectoryForce {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    try {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
        Write-ReleaseLog "Removed: $Path"
        return
    } catch {
        Write-ReleaseLog "WARN: Remove-Item failed for $Path ($($_.Exception.Message)); trying robocopy mirror"
    }

    $empty = Join-Path $env:TEMP ("jenkins-empty-{0}" -f [guid]::NewGuid().ToString('n'))
    try {
        New-Item -ItemType Directory -Path $empty -Force | Out-Null
        & robocopy $empty $Path /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
        if (-not (Test-Path -LiteralPath $Path)) {
            Write-ReleaseLog "Removed via robocopy mirror: $Path"
        } else {
            Write-ReleaseLog "WARN: could not fully remove: $Path"
        }
    } finally {
        Remove-Item -LiteralPath $empty -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$ws = Get-NormalizedPath -Path $Workspace
if (-not $ws) {
    Write-ReleaseLog "Workspace does not exist: $Workspace"
    exit 0
}

Write-ReleaseLog "Releasing locks for: $ws"

$currentPid = $PID
$parentPid = (Get-CimInstance Win32_Process -Filter "ProcessId=$currentPid" -ErrorAction SilentlyContinue).ParentProcessId
$protected = @($currentPid)
if ($parentPid) { $protected += $parentPid }

$killNames = @('java.exe', 'python.exe', 'python3.exe', 'node.exe')
$stopped = 0

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        ($protected -notcontains $_.ProcessId) -and
        ($killNames -contains $_.Name.ToLower()) -and
        (Test-ProcessUsesWorkspace -CommandLine $_.CommandLine -WorkspacePath $ws)
    } |
    ForEach-Object {
        $snippet = $_.CommandLine
        if ($snippet.Length -gt 140) { $snippet = $snippet.Substring(0, 140) + '...' }
        Write-ReleaseLog "Stopping PID $($_.ProcessId) $($_.Name): $snippet"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $stopped++
    }

if ($stopped -gt 0) {
    Start-Sleep -Seconds $GraceSeconds
}

$generatedDirs = @(
    '.maestro-runtime',
    '.maestro_tmp',
    '.maestro-workspace',
    'reports',
    'logs',
    'status',
    'collected-artifacts',
    'build-summary',
    '.maestro',
    'temp',
    'temp-runners',
    'test-results',
    'maestro-report',
    'ai-doctor\artifacts'
)

foreach ($dir in $generatedDirs) {
    Remove-DirectoryForce -Path (Join-Path $ws $dir)
}

Write-ReleaseLog "Done (stopped $stopped stale process(es))"
exit 0
