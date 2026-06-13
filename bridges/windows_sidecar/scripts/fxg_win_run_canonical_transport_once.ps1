# FXG Windows - Run forward then reverse canonical transport once.
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ok = $true
$err = $null
try {
    & (Join-Path $scriptDir "fxg_win_sync_canonical_signals.ps1")
} catch {
    $ok = $false
    $err = $_.Exception.Message
    Write-Host ("FORWARD FAIL: {0}" -f $err) -ForegroundColor Red
}
try {
    & (Join-Path $scriptDir "fxg_win_sync_bridge_log_back.ps1")
} catch {
    $ok = $false
    $err = $_.Exception.Message
    Write-Host ("REVERSE FAIL: {0}" -f $err) -ForegroundColor Red
}
if ($ok) {
    Write-Host "PASS: canonical transport once (forward + reverse) completed." -ForegroundColor Green
    exit 0
}
Write-Host "FAIL: canonical transport once." -ForegroundColor Red
exit 1
