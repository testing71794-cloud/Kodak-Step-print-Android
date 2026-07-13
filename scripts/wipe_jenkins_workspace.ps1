#Requires -Version 5.1
<#
.SYNOPSIS
  Release locks and wipe a Jenkins workspace without Jenkins deleteDir().

  Replaces deleteDir on Windows Maestro agents. Uses process termination, attrib,
  and robocopy /MIR with retries (Jenkins only retries 3x at 0.1s).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Workspace,

    [ValidateSet('Full', 'ReleaseOnly')]
    [string] $Mode = 'Full',

    [int] $MaxAttempts = 12,

    [int] $WaitSeconds = 3
)

$ErrorActionPreference = 'Continue'

function Write-WipeLog {
    param([string] $Message)
    Write-Host "[wipe-ws] $Message"
}

function Get-NormalizedPath {
    param([string] $Path)
    if (-not $Path) { return $null }
    try {
        if (-not (Test-Path -LiteralPath $Path)) {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
        }
        return (Get-Item -LiteralPath $Path -ErrorAction Stop).FullName
    } catch {
        return $null
    }
}

function Get-ProtectedProcessIds {
    $ids = New-Object 'System.Collections.Generic.HashSet[int]'
    [void]$ids.Add($PID)

    $procId = $PID
    for ($i = 0; $i -lt 20; $i++) {
        $row = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        if (-not $row -or -not $row.ParentProcessId -or $row.ParentProcessId -eq 0) { break }
        [void]$ids.Add([int]$row.ParentProcessId)
        $procId = [int]$row.ParentProcessId
    }
    return $ids
}

function Test-ProcessUsesWorkspace {
    param(
        [string] $Name,
        [string] $CommandLine,
        [string] $WorkspacePath
    )
    if (-not $CommandLine) { return $false }

    $cl = $CommandLine
    if ($cl -like "*$WorkspacePath*") { return $true }

    $automationMarkers = @(
        'jenkins_atp_stage',
        'run_one_flow_on_device',
        '.maestro-runtime',
        'kodak-atp-android',
        'Kodak Step Print Android',
        'Kodak Step Print\\',
        'kodak-step-print'
    )
    foreach ($m in $automationMarkers) {
        if ($cl -like "*$m*") { return $true }
    }

    if ($Name -ieq 'java.exe') {
        if ($cl -match '(?i)-Duser\.home=.*maestro-runtime') { return $true }
        if ($cl -match '(?i)classpath.*maestro') { return $true }
    }
    return $false
}

function Stop-StaleWorkspaceProcesses {
    param([string] $WorkspacePath)

    $protected = Get-ProtectedProcessIds
    $killNames = @('java.exe', 'python.exe', 'python3.exe', 'node.exe', 'cmd.exe', 'conhost.exe')
    $stopped = 0

    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            ($protected -notcontains [int]$_.ProcessId) -and
            ($killNames -contains $_.Name.ToLower()) -and
            (Test-ProcessUsesWorkspace -Name $_.Name -CommandLine $_.CommandLine -WorkspacePath $WorkspacePath)
        } |
        ForEach-Object {
            $snippet = $_.CommandLine
            if ($null -ne $snippet -and $snippet.Length -gt 160) {
                $snippet = $snippet.Substring(0, 160) + '...'
            }
            Write-WipeLog "Stopping PID $($_.ProcessId) $($_.Name): $snippet"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            $stopped++
        }

    if ($stopped -gt 0) {
        Start-Sleep -Seconds $WaitSeconds
    }
    return $stopped
}

function Clear-TreeForce {
    param([string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) { return $true }

    try {
        cmd.exe /c "attrib -R `"$Path\*`" /S /D >nul 2>&1"
    } catch { }

    try {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
        return $true
    } catch {
        Write-WipeLog "WARN: Remove-Item failed for $Path ($($_.Exception.Message))"
    }

    $empty = Join-Path $env:TEMP ("jenkins-empty-{0}" -f [guid]::NewGuid().ToString('n'))
    try {
        New-Item -ItemType Directory -Path $empty -Force | Out-Null
        & robocopy $empty $Path /MIR /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
        return -not (Test-Path -LiteralPath $Path)
    } catch {
        Write-WipeLog "WARN: robocopy mirror failed for $Path ($($_.Exception.Message))"
        return $false
    } finally {
        Remove-Item -LiteralPath $empty -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Clear-WorkspaceContents {
    param([string] $WorkspacePath)

    if (-not (Test-Path -LiteralPath $WorkspacePath)) {
        New-Item -ItemType Directory -Path $WorkspacePath -Force | Out-Null
        return $true
    }

    $empty = Join-Path $env:TEMP ("jenkins-empty-{0}" -f [guid]::NewGuid().ToString('n'))
    try {
        New-Item -ItemType Directory -Path $empty -Force | Out-Null
        try {
            cmd.exe /c "attrib -R `"$WorkspacePath\*`" /S /D >nul 2>&1"
        } catch { }

        & robocopy $empty $WorkspacePath /MIR /R:3 /W:3 /NFL /NDL /NJH /NJS /NP | Out-Null
        $rc = $LASTEXITCODE
        if ($rc -ge 8) {
            Write-WipeLog "WARN: robocopy workspace mirror exit code $rc"
            return $false
        }
        return $true
    } catch {
        Write-WipeLog "WARN: workspace mirror failed ($($_.Exception.Message))"
        return $false
    } finally {
        Remove-Item -LiteralPath $empty -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-WorkspaceWipe {
    param([string] $WorkspacePath)

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        Write-WipeLog "Attempt $attempt/$MaxAttempts for $WorkspacePath"
        $null = Stop-StaleWorkspaceProcesses -WorkspacePath $WorkspacePath

        if ($Mode -eq 'ReleaseOnly') {
            $generatedDirs = @(
                '.maestro-runtime', '.maestro_tmp', '.maestro-workspace',
                'reports', 'logs', 'status', 'collected-artifacts', 'build-summary',
                '.maestro', 'temp', 'temp-runners', 'test-results', 'maestro-report',
                'ai-doctor\artifacts'
            )
            foreach ($dir in $generatedDirs) {
                [void](Clear-TreeForce -Path (Join-Path $WorkspacePath $dir))
            }
            Write-WipeLog "ReleaseOnly complete for $WorkspacePath"
            return $true
        }

        if (Clear-WorkspaceContents -WorkspacePath $WorkspacePath) {
            $left = @(Get-ChildItem -LiteralPath $WorkspacePath -Force -ErrorAction SilentlyContinue)
            if ($left.Count -eq 0) {
                Write-WipeLog "Workspace emptied: $WorkspacePath"
                return $true
            }
            Write-WipeLog "WARN: $($left.Count) item(s) remain; retrying"
        }

        Start-Sleep -Seconds $WaitSeconds
    }

    Write-WipeLog "ERROR: could not fully wipe $WorkspacePath after $MaxAttempts attempts"
    return $false
}

$ws = Get-NormalizedPath -Path $Workspace
if (-not $ws) {
    Write-WipeLog "Could not resolve workspace: $Workspace"
    exit 1
}

Write-WipeLog "Mode=$Mode Target=$ws"
$ok = Invoke-WorkspaceWipe -WorkspacePath $ws
if ($ok) { exit 0 }
if ($Mode -eq 'ReleaseOnly') {
    Write-WipeLog "ReleaseOnly finished with warnings (non-fatal)"
    exit 0
}
Write-WipeLog "ERROR: Full wipe incomplete for $ws"
exit 1
