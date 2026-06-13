# Install Windows Sidecar Bridge (parallel_windows_sidecar_bridge_v1)
# Run from repo root or bridges/windows_sidecar
# Prerequisites: Python 3.11+, MT5 installed and logged in

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)

Write-Host "Windows Sidecar Install - bridge_id: parallel_windows_sidecar_bridge_v1"
Write-Host "Sidecar root: $sidecarRoot"
Write-Host ""

# Create .env from .env.example if missing
$envExample = Join-Path $sidecarRoot ".env.example"
$envFile = Join-Path $sidecarRoot ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "Created .env from .env.example - EDIT with your SIDECAR_API_KEY, MT5_* values"
} else {
    Write-Host ".env exists"
}

# Install Python deps
$reqFile = Join-Path $sidecarRoot "requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "Installing Python dependencies..."
    python -m pip install -r $reqFile --quiet
    Write-Host "Done"
} else {
    Write-Host "requirements.txt not found"
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit $envFile - set SIDECAR_API_KEY, MT5_TERMINAL_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER"
Write-Host "2. Run .\scripts\start_windows_sidecar.ps1"
Write-Host "3. Run .\scripts\verify_windows_sidecar.ps1"
