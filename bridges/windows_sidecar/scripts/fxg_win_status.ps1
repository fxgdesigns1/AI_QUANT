# FXG Windows Sidecar - Status (parallel_windows_sidecar_bridge_v1)

$ErrorActionPreference = "SilentlyContinue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $sidecarRoot ".env"
$bindPort = 8877

# Load .env for bind_host
$bindHost = "127.0.0.1"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*BIND_HOST=(.*)$') { $bindHost = $matches[1].Trim() }
        if ($_ -match '^\s*BIND_PORT=(.*)$') { $script:bindPortOverride = $matches[1].Trim() }
    }
}
if ($script:bindPortOverride) { $bindPort = $script:bindPortOverride }

$mt5Proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
$mt5Running = ($null -ne $mt5Proc)

$conn = Get-NetTCPConnection -LocalPort $bindPort -State Listen -ErrorAction SilentlyContinue
$sidecarRunning = ($null -ne $conn)
$sidecarPid = if ($conn) { $conn.OwningProcess } else { $null }

$lanIp = $null
try {
    $lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.' } | Select-Object -First 1).IPAddress
} catch { }

Write-Host "=== FXG Windows Sidecar Status ===" -ForegroundColor Cyan
Write-Host "MT5:          $(if ($mt5Running) { 'RUNNING' } else { 'STOPPED' })" -ForegroundColor $(if ($mt5Running) { 'Green' } else { 'Yellow' })
Write-Host "Sidecar:      $(if ($sidecarRunning) { "RUNNING (PID $sidecarPid)" } else { 'STOPPED' })" -ForegroundColor $(if ($sidecarRunning) { 'Green' } else { 'Red' })
Write-Host "Bind:         ${bindHost}:${bindPort}"
Write-Host "Local URL:    http://127.0.0.1:${bindPort}"
if ($lanIp) { Write-Host "LAN URL:      http://${lanIp}:${bindPort}" }
Write-Host "Bridge ID:    parallel_windows_sidecar_bridge_v1"
Write-Host "Execution:    canonical_mac_file_bridge_v1 (unchanged)"
Write-Host "Data/Diag:    parallel_windows_sidecar_bridge_v1 (read-only)"

$summary = if ($sidecarRunning -and $mt5Running) { "GREEN" } elseif ($sidecarRunning) { "YELLOW (MT5 not running)" } else { "RED (Sidecar down)" }
Write-Host "---" -ForegroundColor Cyan
Write-Host "Summary: $summary" -ForegroundColor $(if ($summary -eq "GREEN") { 'Green' } elseif ($summary -match "YELLOW") { 'Yellow' } else { 'Red' })
