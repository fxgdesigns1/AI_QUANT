# FXG Windows Sidecar - Debug Bindings (parallel_windows_sidecar_bridge_v1)

$ErrorActionPreference = "SilentlyContinue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $sidecarRoot ".env"
$bindPort = 8877

Write-Host "=== FXG Sidecar Bindings Debug ===" -ForegroundColor Cyan

# .env redacted
if (Test-Path $envFile) {
    Write-Host ".env (redacted):" -ForegroundColor Cyan
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*#') { Write-Host $_ }
        elseif ($_ -match '^\s*SIDECAR_API_KEY=') { Write-Host "SIDECAR_API_KEY=***redacted***" }
        elseif ($_ -match '^\s*MT5_PASSWORD=') { Write-Host "MT5_PASSWORD=***redacted***" }
        elseif ($_ -match '^\s*([^=]+)=(.*)$') { Write-Host $_ }
    }
} else {
    Write-Host ".env: NOT FOUND" -ForegroundColor Red
}

# netstat for 8877
Write-Host "`nnetstat :8877:" -ForegroundColor Cyan
$netstat = netstat -ano | findstr ":8877"
if ($netstat) { Write-Host $netstat } else { Write-Host "No listener on 8877" -ForegroundColor Yellow }

# Firewall
Write-Host "`nFirewall rule (TCP 8877):" -ForegroundColor Cyan
try {
    $fw = Get-NetFirewallRule -DisplayName "*8877*" -ErrorAction SilentlyContinue | Select-Object DisplayName, Enabled
    if ($fw) { $fw | Format-Table -AutoSize } else { Write-Host "No rule found matching 8877" }
} catch { Write-Host $_.Exception.Message }

# LAN IP
Write-Host "`nLAN IP:" -ForegroundColor Cyan
try {
    $lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.' } | Select-Object -First 1).IPAddress
    Write-Host "LAN: $lanIp"
    Write-Host "LAN URL: http://${lanIp}:8877"
} catch { Write-Host $_.Exception.Message }
