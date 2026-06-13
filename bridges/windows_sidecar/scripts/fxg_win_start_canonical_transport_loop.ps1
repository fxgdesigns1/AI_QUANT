# FXG Windows - Poll every 5s: forward signals then reverse bridge log. Safe to restart (no truncate).
param(
    [int]$PollSeconds = 5
)
$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir)))
if ($env:FXG_REPO_ROOT -and (Test-Path -LiteralPath $env:FXG_REPO_ROOT)) { $repoRoot = $env:FXG_REPO_ROOT }
$artifacts = Join-Path $repoRoot "artifacts"
if (-not (Test-Path -LiteralPath $artifacts)) { New-Item -ItemType Directory -Path $artifacts -Force | Out-Null }
$hbPath = Join-Path $artifacts "windows_transport_heartbeat.json"
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "FXG canonical transport loop (Ctrl+C to stop). PollSeconds=$PollSeconds" -ForegroundColor Cyan

while ($true) {
    $cycleStart = (Get-Date).ToUniversalTime().ToString("o")
    $fwdOk = $true
    $revOk = $true
    $fwdErr = $null
    $revErr = $null
    $deriveErr = $null
    $syncFwdErr = $null
    try {
        & (Join-Path $scriptDir "fxg_win_derive_canonical_ftmo_from_signals_jsonl.ps1") 2>&1 | Out-Null
    } catch {
        $deriveErr = $_.Exception.Message
    }
    try {
        & (Join-Path $scriptDir "fxg_win_sync_canonical_signals.ps1") 2>&1 | Out-Null
    } catch {
        $syncFwdErr = $_.Exception.Message
    }
    if ($deriveErr -or $syncFwdErr) {
        $fwdOk = $false
        $parts = @()
        if ($deriveErr) { $parts += "derive:$deriveErr" }
        if ($syncFwdErr) { $parts += "sync:$syncFwdErr" }
        $fwdErr = ($parts -join " | ")
    }
    try {
        & (Join-Path $scriptDir "fxg_win_sync_bridge_log_back.ps1") 2>&1 | Out-Null
    } catch {
        $revOk = $false
        $revErr = $_.Exception.Message
    }
    $cycleEnd = (Get-Date).ToUniversalTime().ToString("o")
    $hb = [ordered]@{
        ts_utc = $cycleEnd
        cycle_started_utc = $cycleStart
        cycle_ended_utc = $cycleEnd
        forward_ok = $fwdOk
        reverse_ok = $revOk
        forward_error = $fwdErr
        reverse_error = $revErr
        pid = $PID
    }
    ($hb | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath $hbPath -Encoding UTF8
    Start-Sleep -Seconds $PollSeconds
}
