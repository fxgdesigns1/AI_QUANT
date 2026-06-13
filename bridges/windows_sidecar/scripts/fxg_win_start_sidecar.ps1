# FXG Windows Sidecar - Start (parallel_windows_sidecar_bridge_v1)
# Run from repo root. Loads .env, validates config, starts sidecar.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))
$envFile = Join-Path $sidecarRoot ".env"
$pythonExe = Join-Path $sidecarRoot ".venv\Scripts\python.exe"

# Load .env
if (-not (Test-Path $envFile)) {
    Write-Host "FAIL: .env not found at $envFile" -ForegroundColor Red
    exit 1
}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

# Validate without printing secrets
$apiKey = $env:SIDECAR_API_KEY
if (-not $apiKey -or $apiKey.Length -lt 8) {
    Write-Host "FAIL: SIDECAR_API_KEY missing or invalid in .env" -ForegroundColor Red
    exit 1
}

$mt5Path = $env:MT5_TERMINAL_PATH
if (-not $mt5Path -or -not (Test-Path $mt5Path)) {
    Write-Host "FAIL: MT5_TERMINAL_PATH not set or path does not exist: $mt5Path" -ForegroundColor Red
    exit 1
}

$bindHost = if ($env:BIND_HOST) { $env:BIND_HOST } else { "127.0.0.1" }
$bindPort = if ($env:BIND_PORT) { $env:BIND_PORT } else { "8877" }

if (-not (Test-Path $pythonExe)) {
    Write-Host "FAIL: venv not found at $pythonExe. Run install_windows_sidecar.ps1" -ForegroundColor Red
    exit 1
}

# Check if already running
$existing = Get-NetTCPConnection -LocalPort $bindPort -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Sidecar already listening on port $bindPort (PID may vary). Use fxg_win_stop_sidecar.ps1 first." -ForegroundColor Yellow
    Write-Host "URL: http://${bindHost}:${bindPort}" -ForegroundColor Cyan
    exit 0
}

Set-Location $repoRoot
$runPyPath = Join-Path $repoRoot "bridges\windows_sidecar\run.py"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $pythonExe
$psi.Arguments = "`"$runPyPath`""
$psi.WorkingDirectory = $repoRoot
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$proc = [System.Diagnostics.Process]::Start($psi)
# Poll for listen (up to 12s)
$listening = $null
for ($i = 0; $i -lt 12; $i++) {
    Start-Sleep -Seconds 1
    $listening = Get-NetTCPConnection -LocalPort $bindPort -ErrorAction SilentlyContinue
    if ($listening) { break }
}

$listening = Get-NetTCPConnection -LocalPort $bindPort -ErrorAction SilentlyContinue
if ($listening) {
    $sidecarPid = $listening.OwningProcess
    Write-Host "PASS: Sidecar started (PID $sidecarPid)" -ForegroundColor Green
    Write-Host "Bind: ${bindHost}:${bindPort}" -ForegroundColor Cyan
    Write-Host "URL: http://127.0.0.1:${bindPort}" -ForegroundColor Cyan
} else {
    Write-Host "FAIL: Sidecar process started but not listening on port $bindPort" -ForegroundColor Red
    exit 1
}
