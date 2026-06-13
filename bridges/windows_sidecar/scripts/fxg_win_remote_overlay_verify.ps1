# FXG Windows - Verify Remote Overlay and Sidecar
$ErrorActionPreference = "Stop"
$tailscaleExe = "C:\Program Files\Tailscale\tailscale.exe"
$ok = $true
if (-not (Test-Path $tailscaleExe)) { Write-Host "FAIL: Tailscale not installed"; exit 1 }
$ip = (& $tailscaleExe ip -4 2>&1).Trim()
if (-not ($ip -match '^\d+\.\d+\.\d+\.\d+$')) { Write-Host "WARN: Tailscale not connected (run tailscale up)"; $ok = $false }
$listener = Get-NetTCPConnection -LocalPort 8877 -ErrorAction SilentlyContinue
if (-not $listener) { Write-Host "WARN: Sidecar not listening on 8877"; $ok = $false }
Write-Host "Tailscale IP: $ip"
Write-Host "Sidecar: $(if($listener){'OK'}else{'Not running'})"
if ($ok) { Write-Host "PASS"; exit 0 } else { exit 1 }
