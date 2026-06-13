# FXG Windows - Verify paths, state, last sync, duplicate sanity (spot-check).
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir)))
if ($env:FXG_REPO_ROOT -and (Test-Path -LiteralPath $env:FXG_REPO_ROOT)) { $repoRoot = $env:FXG_REPO_ROOT }

$srcSig = Join-Path $repoRoot "logs\signals_ftmo_demo2.jsonl"
$dstBridgeRepo = Join-Path $repoRoot "logs\ftmo_bridge_log.jsonl"
$mt5Known = "C:\Users\gavin\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files"
$mt5Files = $mt5Known
if ($env:FXG_MT5_FILES_DIR -and (Test-Path -LiteralPath $env:FXG_MT5_FILES_DIR)) { $mt5Files = $env:FXG_MT5_FILES_DIR }
$dstSig = Join-Path $mt5Files "signals_ftmo_demo2.jsonl"
$srcBridgeMt5 = Join-Path $mt5Files "ftmo_bridge_log.jsonl"

$statePath = Join-Path $repoRoot "artifacts\windows_transport_state.json"
$statusPath = Join-Path $repoRoot "artifacts\windows_transport_status.json"
$hbPath = Join-Path $repoRoot "artifacts\windows_transport_heartbeat.json"

$result = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    paths_ok = @{}
    state_ok = $false
    last_success_utc = $null
    sample_propagation_note = "Compare last lines of repo signal file and MT5 signal file after a forward sync."
}

$result.paths_ok["shared_repo_signals"] = Test-Path -LiteralPath $srcSig
$result.paths_ok["shared_repo_bridge_log"] = Test-Path -LiteralPath $dstBridgeRepo
$result.paths_ok["mt5_signals"] = Test-Path -LiteralPath $dstSig
$result.paths_ok["mt5_bridge_log"] = Test-Path -LiteralPath $srcBridgeMt5

if (Test-Path -LiteralPath $statePath) {
    $result.state_ok = $true
    $st = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($st.PSObject.Properties.Name -contains "last_success_utc") {
        $result.last_success_utc = $st.last_success_utc
    }
    if ($st.PSObject.Properties.Name -contains "reverse_last_success_utc") {
        $result["reverse_last_success_utc"] = $st.reverse_last_success_utc
    }
}

$result["status_file_present"] = Test-Path -LiteralPath $statusPath
$result["heartbeat_file_present"] = Test-Path -LiteralPath $hbPath

# Duplicate explosion check: count distinct signal_id in MT5 dest vs line count (rough)
$utf8 = New-Object System.Text.UTF8Encoding $false
function Count-DupeSignalIds {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return @{ lines = 0; distinct_ids = 0 } }
    $lines = [System.IO.File]::ReadAllLines($Path, $utf8) | Where-Object { $_.Trim().Length -gt 0 }
    $ids = @{}
    foreach ($ln in $lines) {
        try {
            $o = $ln | ConvertFrom-Json
            if ($o.PSObject.Properties.Name -contains "signal_id" -and $o.signal_id) {
                $ids[[string]$o.signal_id] = $true
            }
        } catch { }
    }
    return @{ lines = $lines.Count; distinct_ids = $ids.Keys.Count }
}

$result["mt5_signals_line_vs_distinct_signal_id"] = Count-DupeSignalIds -Path $dstSig

$allPaths = $result.paths_ok.Values | ForEach-Object { $_ } | Where-Object { $_ -eq $false }
if ($allPaths.Count -eq 0 -and $result.state_ok) {
    Write-Host "VERIFY: PASS (paths and state present)." -ForegroundColor Green
} else {
    Write-Host "VERIFY: FAIL or INCOMPLETE (see JSON)." -ForegroundColor Yellow
}

$result | ConvertTo-Json -Depth 8
