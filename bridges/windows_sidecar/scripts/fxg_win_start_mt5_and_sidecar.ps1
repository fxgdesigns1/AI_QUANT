# FXG Windows Sidecar - Start MT5 + Sidecar (parallel_windows_sidecar_bridge_v1)
# Ensures MT5 is running, then starts sidecar and verifies.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$envFile = Join-Path $sidecarRoot ".env"

# Load .env
if (-not (Test-Path $envFile)) {
    Write-Host "FAIL: .env not found" -ForegroundColor Red
    exit 1
}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

$mt5Path = $env:MT5_TERMINAL_PATH
if (-not $mt5Path -or -not (Test-Path $mt5Path)) {
    Write-Host "FAIL: MT5_TERMINAL_PATH not set or invalid" -ForegroundColor Red
    exit 1
}

$bindPort = if ($env:BIND_PORT) { $env:BIND_PORT } else { "8877" }
$baseUrl = "http://127.0.0.1:${bindPort}"

# Ensure MT5 is running
$mt5Proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
if (-not $mt5Proc) {
    Write-Host "Starting MT5..." -ForegroundColor Cyan
    Start-Process -FilePath $mt5Path
    Start-Sleep -Seconds 8
} else {
    Write-Host "MT5 already running" -ForegroundColor Green
}

# Start sidecar (delegate to fxg_win_start_sidecar)
& (Join-Path $scriptDir "fxg_win_start_sidecar.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Quick verification
$apiKey = $env:SIDECAR_API_KEY
$headers = @{ "x-api-key" = $apiKey }
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Headers $headers -Method Get
    $account = Invoke-RestMethod -Uri "$baseUrl/account" -Headers $headers -Method Get
    if ($health.service_up -and $account.login) {
        Write-Host "PASS: Health OK, account $($account.login) @ $($account.server)" -ForegroundColor Green
    } else {
        Write-Host "WARN: Sidecar up but account may not be connected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "WARN: Sidecar started but verification failed: $($_.Exception.Message)" -ForegroundColor Yellow
}
