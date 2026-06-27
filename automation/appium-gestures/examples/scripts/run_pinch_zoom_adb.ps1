# DEPRECATED: parallel adb input swipe is NOT real multitouch on Android.
# Use run_pinch_zoom_w3c.bat (Appium W3C Actions) instead.
# This script remains for reference only.
# Usage: .\run_pinch_zoom_adb.ps1 [-Gesture both|pinch-out|pinch-in] [-Device SERIAL]
param(
    [ValidateSet("both", "pinch-out", "pinch-in")]
    [string]$Gesture = "both",
    [string]$Device = $(if ($env:ANDROID_SERIAL) { $env:ANDROID_SERIAL } else { "" })
)

$ErrorActionPreference = "Stop"

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { $adb = "adb" }

if (-not $Device) {
    Write-Error "Device serial required (-Device or ANDROID_SERIAL)"
    exit 1
}

$sizeOut = & $adb -s $Device shell wm size 2>&1 | Out-String
if ($sizeOut -match "(\d+)x(\d+)") {
    $W = [int]$Matches[1]
    $H = [int]$Matches[2]
} else {
    $W = 1080
    $H = 2400
}

$CX = [int]($W * 0.50)
$CY = [int]($H * 0.42)
$Inner = 60
$Outer = 140
$Dur = 650

$moduleRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$outDir = Join-Path $moduleRoot "target\screenshots\adb"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Save-Screenshot($tag) {
    try {
        $ts = Get-Date -Format "yyyyMMdd_HHmmss_fff"
        $path = Join-Path $outDir "${tag}_${ts}.png"
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $adb
        $psi.Arguments = "-s $Device exec-out screencap -p"
        $psi.RedirectStandardOutput = $true
        $psi.UseShellExecute = $false
        $proc = [System.Diagnostics.Process]::Start($psi)
        $ms = New-Object System.IO.MemoryStream
        $proc.StandardOutput.BaseStream.CopyTo($ms)
        $proc.WaitForExit()
        [System.IO.File]::WriteAllBytes($path, $ms.ToArray())
        Write-Host "[INFO] Screenshot $path"
    } catch {
        Write-Host "[WARN] Screenshot skipped: $_"
    }
}

function Invoke-ParallelPinch($spread) {
    if ($spread) {
        $l1 = $CX - $Inner; $l2 = $CX - $Outer
        $r1 = $CX + $Inner; $r2 = $CX + $Outer
        Write-Host "[INFO] pinch-out L ${l1},${CY}->${l2},${CY}  R ${r1},${CY}->${r2},${CY}"
    } else {
        $l1 = $CX - $Outer; $l2 = $CX - $Inner
        $r1 = $CX + $Outer; $r2 = $CX + $Inner
        Write-Host "[INFO] pinch-in L ${l1},${CY}->${l2},${CY}  R ${r1},${CY}->${r2},${CY}"
    }

    $p1 = Start-Process -FilePath $adb -ArgumentList @("-s", $Device, "shell", "input", "swipe", "$l1", "$CY", "$l2", "$CY", "$Dur") -PassThru -NoNewWindow
    $p2 = Start-Process -FilePath $adb -ArgumentList @("-s", $Device, "shell", "input", "swipe", "$r1", "$CY", "$r2", "$CY", "$Dur") -PassThru -NoNewWindow
    Wait-Process -Id $p1.Id, $p2.Id -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds ($Dur + 200)
}

Write-Host "[INFO] viewport=${W}x${H} center=${CX},${CY} gesture=$Gesture device=$Device"

Save-Screenshot "before_pinch"

switch ($Gesture) {
    "pinch-out" { Invoke-ParallelPinch $true }
    "pinch-in"  { Invoke-ParallelPinch $false }
    default {
        Invoke-ParallelPinch $true
        Start-Sleep -Milliseconds 400
        Invoke-ParallelPinch $false
    }
}

Save-Screenshot "after_pinch"
Write-Host "[OK] ADB parallel pinch completed"
exit 0
