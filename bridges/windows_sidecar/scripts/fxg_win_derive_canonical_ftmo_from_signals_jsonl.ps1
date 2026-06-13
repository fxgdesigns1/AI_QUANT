# FXG Windows — Derive canonical lane-010 / FTMO execution stream from aggregate signals log.
# Reads repo logs/signals.jsonl (upstream aggregate); appends bridge_account=ftmo_demo2 lines
# to logs/signals_ftmo_demo2.jsonl when not already present (dedupe by signal_id).
# No producer semantics change: transport-only. Safe to run repeatedly.
$ErrorActionPreference = "Stop"

function Get-FxgRepoRoot {
    param([string]$ScriptDir)
    return (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir)))
}

function Get-FxgUtf8NoBom {
    return New-Object System.Text.UTF8Encoding $false
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

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Get-FxgRepoRoot -ScriptDir $scriptDir
if ($env:FXG_REPO_ROOT -and (Test-Path -LiteralPath $env:FXG_REPO_ROOT)) { $repoRoot = $env:FXG_REPO_ROOT }

$srcAgg = Join-Path $repoRoot "logs\signals.jsonl"
$dstCanon = Join-Path $repoRoot "logs\signals_ftmo_demo2.jsonl"
$logsDir = Join-Path $repoRoot "logs"
if (-not (Test-Path -LiteralPath $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

$artifacts = Join-Path $repoRoot "artifacts"
if (-not (Test-Path -LiteralPath $artifacts)) { New-Item -ItemType Directory -Path $artifacts -Force | Out-Null }
$deriveStatusPath = Join-Path $artifacts "lane010_derive_status.json"

$utf8 = Get-FxgUtf8NoBom

if (-not (Test-Path -LiteralPath $srcAgg)) {
    [System.IO.File]::WriteAllText($srcAgg, "", $utf8)
}
if (-not (Test-Path -LiteralPath $dstCanon)) {
    [System.IO.File]::WriteAllText($dstCanon, "", $utf8)
}

$already = Read-SignalIdsFromFile -Path $dstCanon -Utf8 $utf8

$appended = 0
$skipped_wrong_account = 0
$skipped_bad_json = 0
$skipped_duplicate = 0
$skipped_missing_id = 0

$aggLines = [System.IO.File]::ReadAllLines($srcAgg, $utf8)
foreach ($line in $aggLines) {
    $t = $line.Trim()
    if ($t.Length -eq 0) { continue }
    $obj = $null
    try { $obj = $t | ConvertFrom-Json } catch { $skipped_bad_json++; continue }
    $ba = $null
    if ($obj.PSObject.Properties.Name -contains "bridge_account") { $ba = [string]$obj.bridge_account }
    if ($ba -ne "ftmo_demo2") { $skipped_wrong_account++; continue }
    $sid = $null
    if ($obj.PSObject.Properties.Name -contains "signal_id") { $sid = [string]$obj.signal_id }
    if ([string]::IsNullOrWhiteSpace($sid)) { $skipped_missing_id++; continue }
    if ($already.ContainsKey($sid)) { $skipped_duplicate++; continue }
    $lineToWrite = $t
    if (-not $lineToWrite.EndsWith("`n")) {
        [System.IO.File]::AppendAllText($dstCanon, $lineToWrite + "`n", $utf8)
    } else {
        [System.IO.File]::AppendAllText($dstCanon, $lineToWrite, $utf8)
    }
    $already[$sid] = $true
    $appended++
}

$now = (Get-Date).ToUniversalTime().ToString("o")
$statusOut = [ordered]@{
    phase = "derive_ftmo_from_signals_jsonl"
    ts_utc = $now
    appended = $appended
    skipped_duplicate = $skipped_duplicate
    skipped_wrong_account = $skipped_wrong_account
    skipped_bad_json = $skipped_bad_json
    skipped_missing_signal_id = $skipped_missing_id
    src_aggregate = $srcAgg
    dst_canonical = $dstCanon
    rule = "bridge_account=ftmo_demo2 dedupe_by_signal_id"
}
($statusOut | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $deriveStatusPath -Encoding UTF8

Write-Host ("DERIVE: appended={0} aggregate={1} canonical={2}" -f $appended, $srcAgg, $dstCanon)
