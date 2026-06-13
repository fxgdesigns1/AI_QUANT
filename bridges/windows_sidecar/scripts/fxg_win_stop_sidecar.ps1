# FXG Windows Sidecar - Stop (parallel_windows_sidecar_bridge_v1)
# Stops only the sidecar process on port 8877.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$bindPort = 8877

$conn = Get-NetTCPConnection -LocalPort $bindPort -State Listen -ErrorAction SilentlyContinue
if (-not $conn) {
    Write-Host "Sidecar not listening on port $bindPort (already stopped)" -ForegroundColor Yellow
    exit 0
}

$targetPid = $conn.OwningProcess
$proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host "Port $bindPort in use but process not found" -ForegroundColor Yellow
    exit 0
}

# Confirm it's the sidecar (python running run.py)
$cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$targetPid").CommandLine
if ($cmdLine -match "run\.py" -or $cmdLine -match "windows_sidecar") {
    Stop-Process -Id $targetPid -Force
    Write-Host "Stopped sidecar (PID $targetPid)" -ForegroundColor Green
} else {
    Write-Host "WARN: Process on port $bindPort does not appear to be sidecar. Not stopping." -ForegroundColor Yellow
    Write-Host "Command: $cmdLine"
}
