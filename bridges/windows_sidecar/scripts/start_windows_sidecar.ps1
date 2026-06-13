# Start Windows Sidecar Bridge (parallel_windows_sidecar_bridge_v1)
# Run from repo root: .\bridges\windows_sidecar\scripts\start_windows_sidecar.ps1

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)

# Load .env if present
$envFile = Join-Path $sidecarRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

Set-Location $repoRoot
$pythonExe = Join-Path $sidecarRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) { $pythonExe = "python" }
$bindHost = if ($env:BIND_HOST) { $env:BIND_HOST } else { "127.0.0.1" }
$bindPort = if ($env:BIND_PORT) { $env:BIND_PORT } else { "8877" }
Write-Host "Starting Windows Sidecar at ${bindHost}:${bindPort} (bridge_id: parallel_windows_sidecar_bridge_v1)"
& $pythonExe bridges/windows_sidecar/run.py
