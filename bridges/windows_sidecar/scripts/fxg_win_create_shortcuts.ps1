# FXG Windows Sidecar - Create Desktop Shortcuts (parallel_windows_sidecar_bridge_v1)
# Creates shortcuts for Start, Stop, Restart, Status, Healthcheck, Debug.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))
$desktop = [Environment]::GetFolderPath("Desktop")

$shortcuts = @(
    @{ Name = "FXG Start Sidecar"; Script = "fxg_win_start_sidecar.ps1" },
    @{ Name = "FXG Start MT5+Sidecar"; Script = "fxg_win_start_mt5_and_sidecar.ps1" },
    @{ Name = "FXG Stop Sidecar"; Script = "fxg_win_stop_sidecar.ps1" },
    @{ Name = "FXG Restart Sidecar"; Script = "fxg_win_restart_sidecar.ps1" },
    @{ Name = "FXG Sidecar Status"; Script = "fxg_win_status.ps1" },
    @{ Name = "FXG Sidecar Healthcheck"; Script = "fxg_win_healthcheck.ps1" },
    @{ Name = "FXG Sidecar Debug"; Script = "fxg_win_debug_sidecar.ps1" }
)

foreach ($s in $shortcuts) {
    $scriptPath = Join-Path $scriptDir $s.Script
    if (-not (Test-Path $scriptPath)) { Write-Host "Skip: $($s.Script) not found"; continue }
    $target = "powershell.exe"
    $argStr = "-NoExit -ExecutionPolicy Bypass -File `"$scriptPath`""
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut((Join-Path $desktop "$($s.Name).lnk"))
    $sc.TargetPath = $target
    $sc.Arguments = $argStr
    $sc.WorkingDirectory = $repoRoot
    $sc.Save()
    Write-Host "Created: $($s.Name)" -ForegroundColor Green
}

Write-Host "Shortcuts saved to Desktop" -ForegroundColor Cyan
