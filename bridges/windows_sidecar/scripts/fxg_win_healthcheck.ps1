# FXG Windows Sidecar - Healthcheck (parallel_windows_sidecar_bridge_v1)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $sidecarRoot ".env"

if (-not (Test-Path $envFile)) {
    Write-Host "FAIL: .env not found" -ForegroundColor Red
    exit 1
}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*SIDECAR_API_KEY=(.*)$') { $script:apiKey = $matches[1].Trim() }
    if ($_ -match '^\s*BIND_PORT=(.*)$') { $script:portOverride = $matches[1].Trim() }
}
$bindPort = if ($script:portOverride) { $script:portOverride } else { "8877" }
$baseUrl = "http://127.0.0.1:${bindPort}"
$headers = @{ "x-api-key" = $script:apiKey }

$allPass = $true
$failureBucket = $null

# Health
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Headers $headers -TimeoutSec 5
    Write-Host "/health: service_up=$($health.service_up), terminal=$($health.terminal_connected), account=$($health.account_connected)" -ForegroundColor $(if ($health.service_up) { 'Green' } else { 'Yellow' })
    if (-not $health.service_up) { $allPass = $false; $failureBucket = "health_degraded" }
} catch {
    if ($_.Exception.Message -match "401") { Write-Host "/health: 401 Unauthorized (check API key)" -ForegroundColor Red }
    elseif ($_.Exception.Message -match "refused|Unable to connect") { Write-Host "/health: Connection refused (sidecar not running)" -ForegroundColor Red }
    else { Write-Host "/health: $($_.Exception.Message)" -ForegroundColor Red }
    $allPass = $false
    $failureBucket = "connection_failed"
}

# Diagnostics
try {
    $diag = Invoke-RestMethod -Uri "$baseUrl/diagnostics" -Headers $headers -TimeoutSec 5
    Write-Host "/diagnostics: mt5_initialize_ok=$($diag.mt5_initialize_ok)" -ForegroundColor Cyan
} catch { Write-Host "/diagnostics: $($_.Exception.Message)" -ForegroundColor Yellow }

# Account
try {
    $acc = Invoke-RestMethod -Uri "$baseUrl/account" -Headers $headers -TimeoutSec 5
    Write-Host "/account: login=$($acc.login), server=$($acc.server), balance=$($acc.balance)" -ForegroundColor Cyan
    if (-not $acc.login) { $allPass = $false }
} catch { Write-Host "/account: $($_.Exception.Message)" -ForegroundColor Yellow; $allPass = $false }

# Tick
try {
    $tick = Invoke-RestMethod -Uri "$baseUrl/symbols/EURUSD/tick" -Headers $headers -TimeoutSec 5
    if ($tick.failure_bucket) {
        Write-Host "/symbols/EURUSD/tick: $($tick.failure_bucket)" -ForegroundColor Yellow
        if ($tick.recommended_fix) { Write-Host "  recommended_fix: $($tick.recommended_fix)" -ForegroundColor Gray }
        if ($tick.broker_symbol_actual) { Write-Host "  broker_symbol_actual: $($tick.broker_symbol_actual) - try /symbols/$($tick.broker_symbol_actual)/tick" -ForegroundColor Cyan }
        $allPass = $false
    } else {
        Write-Host "/symbols/EURUSD/tick: bid=$($tick.bid), ask=$($tick.ask)" -ForegroundColor Cyan
    }
} catch { Write-Host "/symbols/EURUSD/tick: $($_.Exception.Message)" -ForegroundColor Yellow; $allPass = $false }

Write-Host "---"
if ($allPass) {
    Write-Host "PASS: Healthcheck OK" -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAIL: Healthcheck failed (bucket: $failureBucket)" -ForegroundColor Red
    exit 1
}
