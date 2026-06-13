# FXG Windows Sidecar - Restart (parallel_windows_sidecar_bridge_v1)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $scriptDir "fxg_win_stop_sidecar.ps1")
Start-Sleep -Seconds 2
& (Join-Path $scriptDir "fxg_win_start_sidecar.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$sidecarRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $sidecarRoot ".env"
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*SIDECAR_API_KEY=(.*)$') { $script:apiKey = $matches[1].Trim() }
}
$bindPort = 8877
$headers = @{ "x-api-key" = $script:apiKey }
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:${bindPort}/health" -Headers $headers
    if ($r.service_up) { Write-Host "PASS: Restart complete, /health OK" -ForegroundColor Green } else { Write-Host "FAIL: service_up=false" -ForegroundColor Red; exit 1 }
} catch {
    Write-Host "FAIL: /health unreachable after restart" -ForegroundColor Red
    exit 1
}
