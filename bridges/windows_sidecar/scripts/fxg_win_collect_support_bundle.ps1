# FXG Windows Sidecar - Collect Support Bundle (parallel_windows_sidecar_bridge_v1)

$ErrorActionPreference = "SilentlyContinue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))
$envFile = Join-Path $sidecarRoot ".env"
$bindPort = 8877

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$bundleDir = Join-Path $repoRoot "artifacts\support_bundles\windows"
$bundlePath = Join-Path $bundleDir "fxg_sidecar_bundle_$timestamp"
New-Item -ItemType Directory -Path $bundlePath -Force | Out-Null

Write-Host "Collecting support bundle to $bundlePath" -ForegroundColor Cyan

# Redacted env summary
$envRedacted = @()
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*SIDECAR_API_KEY=') { $envRedacted += "SIDECAR_API_KEY=***redacted***" }
        elseif ($_ -match '^\s*MT5_PASSWORD=') { $envRedacted += "MT5_PASSWORD=***redacted***" }
        elseif ($_ -match '^\s*([^#=]+)=(.*)$') { $envRedacted += $_ }
    }
}
$envRedacted | Out-File (Join-Path $bundlePath "env_redacted.txt")

# netstat
netstat -ano | findstr ":8877" | Out-File (Join-Path $bundlePath "netstat_8877.txt")

# API responses (if sidecar running)
$apiKey = $null
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*SIDECAR_API_KEY=(.*)$') { $script:apiKey = $matches[1].Trim() }
}
if ($script:apiKey) {
    $headers = @{ "x-api-key" = $script:apiKey }
    try {
        (Invoke-RestMethod -Uri "http://127.0.0.1:${bindPort}/health" -Headers $headers) | ConvertTo-Json | Out-File (Join-Path $bundlePath "health.json")
    } catch { "Error: $($_.Exception.Message)" | Out-File (Join-Path $bundlePath "health.json") }
    try {
        (Invoke-RestMethod -Uri "http://127.0.0.1:${bindPort}/diagnostics" -Headers $headers) | ConvertTo-Json | Out-File (Join-Path $bundlePath "diagnostics.json")
    } catch { "Error: $($_.Exception.Message)" | Out-File (Join-Path $bundlePath "diagnostics.json") }
    try {
        (Invoke-RestMethod -Uri "http://127.0.0.1:${bindPort}/account" -Headers $headers) | ConvertTo-Json | Out-File (Join-Path $bundlePath "account.json")
    } catch { "Error: $($_.Exception.Message)" | Out-File (Join-Path $bundlePath "account.json") }
}

# Process info
$conn = Get-NetTCPConnection -LocalPort $bindPort -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $procId = $conn.OwningProcess
    (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue) | Select-Object ProcessId, CommandLine | ConvertTo-Json | Out-File (Join-Path $bundlePath "sidecar_process.json")
}

# Discovery summary
@{
    collected_at = (Get-Date).ToString("o")
    repo_root = $repoRoot
    sidecar_root = $sidecarRoot
    bind_port = $bindPort
} | ConvertTo-Json | Out-File (Join-Path $bundlePath "discovery.json")

Write-Host "PASS: Bundle saved to $bundlePath" -ForegroundColor Green
