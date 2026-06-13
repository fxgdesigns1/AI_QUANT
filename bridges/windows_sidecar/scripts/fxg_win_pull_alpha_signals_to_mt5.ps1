# FXG Windows - Direct pull: ALPHA canonical signals_ftmo_demo2.jsonl -> active MT5 MQL5/Files/signals_ftmo_demo2.jsonl
# Append-only, dedupe by signal_id, never truncates destination.
#
# Requirements:
# - gcloud installed and authenticated for compute scp
# - ALPHA instance reachable: fxg-quant-paper-e2-micro (zone us-east1-b, project fxg-ai-trading)
#
# Overrides (optional):
# - FXG_ALPHA_INSTANCE, FXG_ALPHA_ZONE, FXG_ALPHA_PROJECT
# - FXG_ALPHA_SIGNALS_PATH (default /home/aiquant/gcloud-system/logs/signals_ftmo_demo2.jsonl)
# - FXG_MT5_FILES_DIR (if MT5 terminal hash directory changes)
param(
    [string]$AlphaInstance = $env:FXG_ALPHA_INSTANCE,
    [string]$AlphaZone = $env:FXG_ALPHA_ZONE,
    [string]$AlphaProject = $env:FXG_ALPHA_PROJECT,
    [string]$AlphaSignalsPath = $env:FXG_ALPHA_SIGNALS_PATH,
    [string]$Mt5FilesDirOverride = $env:FXG_MT5_FILES_DIR
)

$ErrorActionPreference = "Stop"

function Get-FxgRepoRoot {
    param([string]$ScriptDir)
    return (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir)))
}

function Get-FxgUtf8NoBom { return New-Object System.Text.UTF8Encoding $false }

function Resolve-Mt5FilesDir {
    param([string]$Override)
    if ($Override -and (Test-Path -LiteralPath $Override)) { return $Override }
    $known = "C:\Users\gavin\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files"
    if (Test-Path -LiteralPath $known) { return $known }
    $e = [Environment]::GetEnvironmentVariable("FXG_MT5_FILES_DIR", "Process")
    if ($e -and (Test-Path -LiteralPath $e)) { return $e }
    return $null
}

function Read-SignalIdsFromFile {
    param([string]$Path, [System.Text.UTF8Encoding]$Utf8)
    $ids = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $ids }
    $lines = [System.IO.File]::ReadAllLines($Path, $Utf8)
    if ($null -eq $lines) { return $ids }
    foreach ($line in $lines) {
        $t = $line.Trim()
        if ($t.Length -eq 0) { continue }
        try {
            $o = $t | ConvertFrom-Json
            if ($o.PSObject.Properties.Name -contains "signal_id" -and $o.signal_id) {
                $ids[[string]$o.signal_id] = $true
            }
        } catch { }
    }
    return $ids
}

function Try-ParseSignalIdFromJsonLine {
    param([string]$Line)
    $t = $Line.Trim()
    if ($t.Length -eq 0) { return $null }
    try {
        $o = $t | ConvertFrom-Json
        if ($o.PSObject.Properties.Name -contains "signal_id" -and $o.signal_id) {
            return [string]$o.signal_id
        }
    } catch { }
    return $null
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Get-FxgRepoRoot -ScriptDir $scriptDir
$artifacts = Join-Path $repoRoot "artifacts"
if (-not (Test-Path -LiteralPath $artifacts)) { New-Item -ItemType Directory -Path $artifacts -Force | Out-Null }

$now = (Get-Date).ToUniversalTime().ToString("o")
$utf8 = Get-FxgUtf8NoBom

if (-not $AlphaInstance) { $AlphaInstance = "fxg-quant-paper-e2-micro" }
if (-not $AlphaZone) { $AlphaZone = "us-east1-b" }
if (-not $AlphaProject) { $AlphaProject = "fxg-ai-trading" }
if (-not $AlphaSignalsPath) { $AlphaSignalsPath = "/home/aiquant/gcloud-system/logs/signals_ftmo_demo2.jsonl" }

$mt5Files = Resolve-Mt5FilesDir -Override $Mt5FilesDirOverride
if (-not $mt5Files) { throw "FAIL: Could not resolve MT5 MQL5\Files directory. Set FXG_MT5_FILES_DIR." }
$dst = Join-Path $mt5Files "signals_ftmo_demo2.jsonl"
if (-not (Test-Path -LiteralPath $dst)) { [System.IO.File]::WriteAllText($dst, "", $utf8) }

$tmp = Join-Path $env:TEMP ("signals_ftmo_demo2_alpha_{0}.jsonl" -f ([Guid]::NewGuid().ToString("n")))
$designPath = Join-Path $artifacts "windows_direct_pull_script_design.json"
$statusPath = Join-Path $artifacts "windows_direct_pull_last_status.json"

$design = [ordered]@{
    ts_utc = $now
    alpha = @{
        instance = $AlphaInstance
        zone = $AlphaZone
        project = $AlphaProject
        signals_path = $AlphaSignalsPath
    }
    destination = @{
        mt5_files_dir = $mt5Files
        active_signal_file = $dst
        mode = "append_only_dedup_by_signal_id"
    }
    temp_download = @{ path = $tmp }
    scheduler_recommendation = "Run every 1 minute; Restart on failure."
}
($design | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $designPath -Encoding UTF8

$fetchLines = 0
$validLines = 0
$appendedLines = 0
$duplicateLines = 0
$malformedLines = 0
$newSignalIds = @()
$fetchOk = $false
$lastError = $null

try {
    $srcSpec = ("{0}:{1}" -f $AlphaInstance, $AlphaSignalsPath)
    & gcloud compute scp --project $AlphaProject --zone $AlphaZone $srcSpec $tmp 2>&1 | Out-Null
    $fetchOk = $true

    $seen = Read-SignalIdsFromFile -Path $dst -Utf8 $utf8

    $srcLines = [System.IO.File]::ReadAllLines($tmp, $utf8)
    foreach ($line in $srcLines) {
        $t = $line.Trim()
        if ($t.Length -eq 0) { continue }
        $fetchLines++
        $sid = Try-ParseSignalIdFromJsonLine -Line $t
        if ([string]::IsNullOrWhiteSpace($sid)) { $malformedLines++; continue }
        $validLines++
        if ($seen.ContainsKey($sid)) { $duplicateLines++; continue }
        [System.IO.File]::AppendAllText($dst, $t + "`n", $utf8)
        $seen[$sid] = $true
        $appendedLines++
        $newSignalIds += $sid
    }
} catch {
    $lastError = $_.Exception.Message
} finally {
    try { if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force } } catch { }
}

$status = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    ok = ($fetchOk -and ($null -eq $lastError))
    alpha = @{ instance = $AlphaInstance; zone = $AlphaZone; project = $AlphaProject }
    source_path = $AlphaSignalsPath
    destination = $dst
    counts = @{
        fetched_lines = $fetchLines
        valid_lines = $validLines
        appended_lines = $appendedLines
        duplicate_lines = $duplicateLines
        malformed_lines = $malformedLines
    }
    appended_signal_ids = $newSignalIds
    error = $lastError
}
($status | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $statusPath -Encoding UTF8

if (-not $status.ok) {
    $msg = $lastError
    if (-not $msg) { $msg = "unknown" }
    Write-Host ("FAIL: direct alpha pull ({0})" -f $msg) -ForegroundColor Red
    exit 1
}
Write-Host ("PASS: direct alpha pull appended={0} dup={1} malformed={2}" -f $appendedLines, $duplicateLines, $malformedLines) -ForegroundColor Green
exit 0
