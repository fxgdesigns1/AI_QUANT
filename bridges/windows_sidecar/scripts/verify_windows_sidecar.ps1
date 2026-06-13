# Verify Windows Sidecar Bridge (parallel_windows_sidecar_bridge_v1)
# Run after sidecar is started. Requires SIDECAR_API_KEY in .env or env.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$baseUrl = "http://127.0.0.1:8877"

# Load .env for API key
$envFile = Join-Path $sidecarRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*SIDECAR_API_KEY=(.*)$') {
            $script:apiKey = $matches[1].Trim()
        }
    }
}
if (-not $script:apiKey) { $script:apiKey = $env:SIDECAR_API_KEY }
if (-not $script:apiKey) {
    Write-Host "ERROR: SIDECAR_API_KEY not set. Set in .env or environment."
    exit 1
}

$headers = @{ "x-api-key" = $script:apiKey }

Write-Host "Verifying Windows Sidecar at $baseUrl..."
try {
    $r = Invoke-RestMethod -Uri "$baseUrl/health" -Headers $headers -Method Get
    Write-Host "Health: service_up=$($r.service_up), terminal_connected=$($r.terminal_connected), bridge_id=$($r.bridge_id)"
    if ($r.service_up) { Write-Host "PASS: Sidecar responding" } else { Write-Host "FAIL: service_up=false" }
} catch {
    Write-Host "FAIL: Sidecar unreachable - $($_.Exception.Message)"
    Write-Host "Ensure sidecar is running: .\scripts\start_windows_sidecar.ps1"
    exit 1
}
