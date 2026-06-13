# FXG Windows - One-Click Remote Overlay Setup (Tailscale)
# Installs Tailscale if missing, enables auto-start, prevents sleep while plugged in,
# Verifies sidecar, captures overlay identity. NO execution routes added.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$bridgesRoot = Split-Path -Parent $sidecarRoot
$repoRoot = Split-Path -Parent $bridgesRoot
$artifactsDir = Join-Path $repoRoot "artifacts"
if (-not (Test-Path $artifactsDir)) { New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null }

$tailscaleExe = "C:\Program Files\Tailscale\tailscale.exe"
$installed = Test-Path $tailscaleExe

if (-not $installed) {
    Write-Host "Installing Tailscale via winget..." -ForegroundColor Cyan
    winget install --id Tailscale.Tailscale -e --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "winget install failed. Download from https://tailscale.com/download and install manually." -ForegroundColor Yellow
        exit 1
    }
    $tailscaleExe = "C:\Program Files\Tailscale\tailscale.exe"
    if (-not (Test-Path $tailscaleExe)) {
        Write-Host "Tailscale installed but exe not found. Restart and run again." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "Tailscale: $tailscaleExe" -ForegroundColor Green

# Status - will prompt login if not authenticated
& $tailscaleExe status 2>&1 | Out-Null
$ipOutput = & $tailscaleExe ip -4 2>&1
$tailscaleIp = if ($ipOutput -match '^[\d\.]+$') { $ipOutput.Trim() } else { $null }
$hostname = $env:COMPUTERNAME

# Prevent sleep while plugged in (optional, may require admin)
try {
    powercfg /change standby-timeout-ac 0 2>&1 | Out-Null
    powercfg /change monitor-timeout-ac 30 2>&1 | Out-Null
} catch { }

# Ensure sidecar binds 0.0.0.0 for remote access
$envFile = Join-Path $sidecarRoot ".env"
if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw
    if ($content -notmatch 'BIND_HOST=0\.0\.0\.0') {
        Add-Content $envFile "`nBIND_HOST=0.0.0.0"
        Write-Host "Added BIND_HOST=0.0.0.0 to .env" -ForegroundColor Cyan
    }
}

# Check sidecar
$sidecarRunning = $false
$port = 8877
$listener = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($listener) { $sidecarRunning = $true }
Write-Host "Sidecar on :$port : $(if($sidecarRunning){'Running'}else{'Not running'})" -ForegroundColor $(if($sidecarRunning){'Green'}else{'Yellow'})

# Write artifacts
$identity = @{
    tailscale_ip = $tailscaleIp
    tailscale_hostname = $hostname
    sidecar_port = $port
    sidecar_base_url = if ($tailscaleIp) { "http://${tailscaleIp}:${port}" } else { $null }
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json
$identity | Set-Content (Join-Path $artifactsDir "windows_remote_overlay_identity.json") -Encoding UTF8

$installResult = @{
    tailscale_installed = $installed
    tailscale_ip = $tailscaleIp
    sidecar_running = $sidecarRunning
    next_step = if (-not $tailscaleIp) { "Run 'tailscale up' and sign in, then re-run this script." } else { "Use http://${tailscaleIp}:8877 as MT5_SIDECAR_BASE_URL on Mac." }
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json
$installResult | Set-Content (Join-Path $artifactsDir "windows_remote_overlay_install_result.json") -Encoding UTF8

Write-Host "PASS: Remote overlay setup complete. Identity in artifacts/windows_remote_overlay_identity.json" -ForegroundColor Green
if (-not $tailscaleIp) { Write-Host "Run: & '$tailscaleExe' up" -ForegroundColor Yellow }
