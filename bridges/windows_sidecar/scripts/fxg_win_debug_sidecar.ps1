# FXG Windows Sidecar - Debug (parallel_windows_sidecar_bridge_v1)

$ErrorActionPreference = "SilentlyContinue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$envFile = Join-Path $sidecarRoot ".env"
$bindPort = 8877

# Load API key
$apiKey = $null
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*SIDECAR_API_KEY=(.*)$') { $script:apiKey = $matches[1].Trim() }
        if ($_ -match '^\s*BIND_PORT=(.*)$') { $script:portOverride = $matches[1].Trim() }
    }
}
if ($script:portOverride) { $bindPort = $script:portOverride }

$baseUrl = "http://127.0.0.1:${bindPort}"

Write-Host "=== FXG Sidecar Debug ===" -ForegroundColor Cyan

# Process info
$conn = Get-NetTCPConnection -LocalPort $bindPort -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $procId = $conn.OwningProcess
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue).CommandLine
    Write-Host "Process: PID=$procId" -ForegroundColor Green
    Write-Host "Command: $cmdLine"
} else {
    Write-Host "Process: NOT LISTENING on port $bindPort" -ForegroundColor Red
    Write-Host "Recommended fix: Run fxg_win_start_sidecar.ps1"
}

# API calls
$headers = @{ "x-api-key" = $script:apiKey }
$failureBucket = $null
$recommendedFix = $null

try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Headers $headers -TimeoutSec 5
    Write-Host "/health: $($health | ConvertTo-Json -Compress)"
    if (-not $health.service_up) { $failureBucket = "health_degraded"; $recommendedFix = "Check MT5 is running and logged in" }
    if (-not $health.terminal_connected) { $failureBucket = "mt5_not_connected"; $recommendedFix = "Start MT5 and ensure it is logged in" }
} catch {
    Write-Host "/health: FAIL - $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Message -match "401") { $failureBucket = "auth"; $recommendedFix = "Check SIDECAR_API_KEY in .env" }
    else { $failureBucket = "connection"; $recommendedFix = "Sidecar not running - run fxg_win_start_sidecar.ps1" }
}

try {
    $diag = Invoke-RestMethod -Uri "$baseUrl/diagnostics" -Headers $headers -TimeoutSec 5
    Write-Host "/diagnostics: mt5_initialize_ok=$($diag.mt5_initialize_ok), account_info_available=$($diag.account_info_available)"
} catch { Write-Host "/diagnostics: $($_.Exception.Message)" }

try {
    $acc = Invoke-RestMethod -Uri "$baseUrl/account" -Headers $headers -TimeoutSec 5
    Write-Host "/account: login=$($acc.login), balance=$($acc.balance), server=$($acc.server)"
} catch { Write-Host "/account: $($_.Exception.Message)" }

try {
    $tick = Invoke-RestMethod -Uri "$baseUrl/symbols/EURUSD/tick" -Headers $headers -TimeoutSec 5
    Write-Host "/tick: bid=$($tick.bid), ask=$($tick.ask)"
    if ($tick.failure_bucket) { $failureBucket = $tick.failure_bucket; $recommendedFix = $tick.recommended_fix }
} catch { Write-Host "/tick: $($_.Exception.Message)" }

Write-Host "---"
Write-Host "Likely failure bucket: $failureBucket"
if ($recommendedFix) { Write-Host "Recommended fix: $recommendedFix" -ForegroundColor Yellow }
