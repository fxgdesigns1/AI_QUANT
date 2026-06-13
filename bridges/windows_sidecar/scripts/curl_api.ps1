# Call Windows Sidecar API - loads key from .env, prints each response on its own line
# Usage: .\curl_api.ps1  or  .\curl_api.ps1 health account positions

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $sidecarRoot ".env"

if (-not (Test-Path $envFile)) { Write-Error "Missing .env at $envFile"; exit 1 }
$key = (Get-Content $envFile | Select-String "SIDECAR_API_KEY=" | ForEach-Object { ($_ -split "=", 2)[1].Trim() })
if (-not $key) { Write-Error "SIDECAR_API_KEY not found in .env"; exit 1 }

$base = "http://127.0.0.1:8877"
$endpoints = if ($args.Count -gt 0) { $args } else { "health", "account", "positions", "symbols/EURUSD/tick" }

foreach ($ep in $endpoints) {
    $url = "$base/$ep"
    Write-Host "--- $url ---" -ForegroundColor Cyan
    $r = curl.exe -s -H "x-api-key: $key" $url
    try { $r | ConvertFrom-Json | ConvertTo-Json -Depth 10 } catch { $r }
    Write-Host ""
}
