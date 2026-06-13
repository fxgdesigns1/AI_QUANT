# FXG Windows - Run Probe and Healthcheck from Correct Repo Root
# Callable from any directory. Detects repo root via script location, then runs probe and healthcheck.
# PowerShell 5.1 compatible (no &&).

$ErrorActionPreference = "Stop"

# Detect repo root: this script lives at bridges/windows_sidecar/scripts/, so go up 3 levels
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$bridgesRoot = Split-Path -Parent $sidecarRoot
$repoRoot = (Split-Path -Parent $bridgesRoot)

if (-not (Test-Path (Join-Path $repoRoot "bridges\windows_sidecar\scripts\fxg_win_probe_mt5_identity.ps1"))) {
    Write-Host "FAIL: Repo root not found. Expected probe at $repoRoot\bridges\windows_sidecar\scripts\" -ForegroundColor Red
    exit 1
}

Set-Location $repoRoot
Write-Host "Repo root: $repoRoot" -ForegroundColor Cyan

$probeScript = Join-Path $repoRoot "bridges\windows_sidecar\scripts\fxg_win_probe_mt5_identity.ps1"
$healthScript = Join-Path $repoRoot "bridges\windows_sidecar\scripts\fxg_win_healthcheck.ps1"

$probeOk = $false
$healthOk = $false

# Run probe
Write-Host "--- Running probe ---" -ForegroundColor Yellow
try {
    & $probeScript
    if ($LASTEXITCODE -eq 0) { $probeOk = $true }
} catch {
    Write-Host "Probe error: $_" -ForegroundColor Red
}

# Run healthcheck
Write-Host "--- Running healthcheck ---" -ForegroundColor Yellow
try {
    & $healthScript
    if ($LASTEXITCODE -eq 0) { $healthOk = $true }
} catch {
    Write-Host "Healthcheck error: $_" -ForegroundColor Red
}

Write-Host "--- Summary ---" -ForegroundColor Yellow
if ($probeOk -and $healthOk) {
    Write-Host "PASS: Probe and healthcheck completed" -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAIL: Probe=$probeOk Healthcheck=$healthOk" -ForegroundColor Red
    exit 1
}
