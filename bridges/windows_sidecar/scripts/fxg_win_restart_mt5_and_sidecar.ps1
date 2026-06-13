# FXG Windows Sidecar - Restart MT5 + Sidecar (parallel_windows_sidecar_bridge_v1)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $sidecarRoot ".env"

# Load .env
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

$mt5Path = $env:MT5_TERMINAL_PATH
$bindPort = 8877

# Stop sidecar first
& (Join-Path $scriptDir "fxg_win_stop_sidecar.ps1")
Start-Sleep -Seconds 2

# Stop MT5
$mt5Proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
if ($mt5Proc) {
    Write-Host "Stopping MT5..." -ForegroundColor Cyan
    Stop-Process -Name "terminal64" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

# Start MT5
Write-Host "Starting MT5..." -ForegroundColor Cyan
Start-Process -FilePath $mt5Path
Start-Sleep -Seconds 8

# Start sidecar
& (Join-Path $scriptDir "fxg_win_start_sidecar.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Verify
$apiKey = $env:SIDECAR_API_KEY
$headers = @{ "x-api-key" = $apiKey }
$health = Invoke-RestMethod -Uri "http://127.0.0.1:${bindPort}/health" -Headers $headers
$diag = Invoke-RestMethod -Uri "http://127.0.0.1:${bindPort}/diagnostics" -Headers $headers
$acc = Invoke-RestMethod -Uri "http://127.0.0.1:${bindPort}/account" -Headers $headers

Write-Host "Health: service_up=$($health.service_up), terminal=$($health.terminal_connected), account=$($health.account_connected)" -ForegroundColor Cyan
Write-Host "Account: $($acc.login) @ $($acc.server), balance=$($acc.balance)" -ForegroundColor Cyan
if ($health.service_up -and $health.account_connected) {
    Write-Host "PASS: Restart complete" -ForegroundColor Green
} else {
    Write-Host "WARN: Sidecar up but account may need MT5 login" -ForegroundColor Yellow
}
