# FXG Windows Sidecar - Account Snapshot (parallel_windows_sidecar_bridge_v1)
# Prints balance, equity, margin, profit - operator data (no secrets).

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

$headers = @{ "x-api-key" = $script:apiKey }
try {
    $acc = Invoke-RestMethod -Uri "http://127.0.0.1:${bindPort}/account" -Headers $headers -TimeoutSec 5
} catch {
    Write-Host "FAIL: /account unreachable - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "=== FXG Sidecar Account Snapshot ===" -ForegroundColor Cyan
Write-Host "Login:       $($acc.login)"
Write-Host "Server:      $($acc.server)"
Write-Host "Balance:     $($acc.balance)"
Write-Host "Equity:      $($acc.equity)"
Write-Host "Margin:      $($acc.margin)"
Write-Host "Margin Free: $($acc.margin_free)"
Write-Host "Profit:      $($acc.profit)"
Write-Host "Currency:    $($acc.currency)"
Write-Host "Bridge ID:   $($acc.bridge_id)"
