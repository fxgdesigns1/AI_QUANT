# FXG Windows - Forward sync: shared repo canonical signals -> active MT5 MQL5/Files signals file.
# Upstream: run fxg_win_derive_canonical_ftmo_from_signals_jsonl.ps1 first so logs/signals.jsonl
# is merged into logs/signals_ftmo_demo2.jsonl (dedupe by signal_id).
# Append-only; filter bridge_account=ftmo_demo2; dedupe by signal_id vs destination + state.
# Does not truncate. Does not write to shared repo from MT5.
$ErrorActionPreference = "Stop"

function Get-FxgRepoRoot {
    param([string]$ScriptDir)
    return (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir)))
}

function Get-FxgUtf8NoBom {
    return New-Object System.Text.UTF8Encoding $false
}

function Resolve-Mt5FilesDir {
    param([string]$Override)
    if ($Override -and (Test-Path -LiteralPath $Override)) { return $Override }
    $e = [Environment]::GetEnvironmentVariable("FXG_MT5_FILES_DIR", "Process")
    if ($e -and (Test-Path -LiteralPath $e)) { return $e }
    $known = "C:\Users\gavin\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files"
    if (Test-Path -LiteralPath $known) { return $known }
    $userProfile = [Environment]::GetFolderPath("UserProfile")
    $termBase = Join-Path $userProfile "AppData\Roaming\MetaQuotes\Terminal"
    $wantOrigin = $null
    $proc = Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($proc -and $proc.ExecutablePath) {
        $wantOrigin = [System.IO.Path]::GetDirectoryName($proc.ExecutablePath).TrimEnd('\')
    }
    if (Test-Path $termBase) {
        if ($wantOrigin) {
            foreach ($d in (Get-ChildItem $termBase -Directory)) {
                $originFile = Join-Path $d.FullName "origin.txt"
                if (-not (Test-Path $originFile)) { continue }
                $originText = (Get-Content $originFile -Raw).Trim().TrimEnd('\')
                if ($originText -ne $wantOrigin) { continue }
                $fp = Join-Path $d.FullName "MQL5\Files"
                if (Test-Path $fp) { return $fp }
            }
        }
        foreach ($d in (Get-ChildItem $termBase -Directory)) {
            $fp = Join-Path $d.FullName "MQL5\Files"
            if (Test-Path $fp) { return $fp }
        }
    }
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

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Get-FxgRepoRoot -ScriptDir $scriptDir
if ($env:FXG_REPO_ROOT -and (Test-Path -LiteralPath $env:FXG_REPO_ROOT)) { $repoRoot = $env:FXG_REPO_ROOT }

$src = Join-Path $repoRoot "logs\signals_ftmo_demo2.jsonl"
$mt5Files = Resolve-Mt5FilesDir -Override $null
if (-not $mt5Files) { throw "FAIL: Could not resolve MT5 MQL5\Files directory. Set FXG_MT5_FILES_DIR." }
$dst = Join-Path $mt5Files "signals_ftmo_demo2.jsonl"

$artifacts = Join-Path $repoRoot "artifacts"
if (-not (Test-Path -LiteralPath $artifacts)) { New-Item -ItemType Directory -Path $artifacts -Force | Out-Null }
$statePath = Join-Path $artifacts "windows_transport_state.json"
$statusPath = Join-Path $artifacts "windows_transport_status.json"

$utf8 = Get-FxgUtf8NoBom

if (-not (Test-Path -LiteralPath $src)) {
    [System.IO.File]::WriteAllText($src, "", $utf8)
}

if (-not (Test-Path -LiteralPath $dst)) {
    [System.IO.File]::WriteAllText($dst, "", $utf8)
}

$seenDest = Read-SignalIdsFromFile -Path $dst -Utf8 $utf8

$stateObj = $null
if (Test-Path -LiteralPath $statePath) {
    try { $stateObj = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $stateObj = $null }
}
$lastSeen = @{}
if ($stateObj -and $stateObj.PSObject.Properties.Name -contains "last_seen_signal_ids") {
    $raw = $stateObj.last_seen_signal_ids
    if ($null -ne $raw) {
        if ($raw -is [System.Array]) {
            foreach ($x in $raw) { if ($x) { $lastSeen[[string]$x] = $true } }
        } else {
            $lastSeen[[string]$raw] = $true
        }
    }
}
foreach ($k in $seenDest.Keys) { $lastSeen[$k] = $true }

$srcLines = [System.IO.File]::ReadAllLines($src, $utf8)
$appended = 0
$skipped_wrong_account = 0
$skipped_bad_json = 0
$skipped_duplicate = 0

foreach ($line in $srcLines) {
    $t = $line.Trim()
    if ($t.Length -eq 0) { continue }
    $obj = $null
    try { $obj = $t | ConvertFrom-Json } catch { $skipped_bad_json++; continue }
    $ba = $null
    if ($obj.PSObject.Properties.Name -contains "bridge_account") { $ba = [string]$obj.bridge_account }
    if ($ba -ne "ftmo_demo2") { $skipped_wrong_account++; continue }
    $sid = $null
    if ($obj.PSObject.Properties.Name -contains "signal_id") { $sid = [string]$obj.signal_id }
    if ([string]::IsNullOrWhiteSpace($sid)) { $skipped_bad_json++; continue }
    if ($lastSeen.ContainsKey($sid)) { $skipped_duplicate++; continue }
    $lineToWrite = $t
    if (-not $lineToWrite.EndsWith("`n")) {
        [System.IO.File]::AppendAllText($dst, $lineToWrite + "`n", $utf8)
    } else {
        [System.IO.File]::AppendAllText($dst, $lineToWrite, $utf8)
    }
    $lastSeen[$sid] = $true
    $appended++
}

$idsOut = @($lastSeen.Keys | Sort-Object)
$now = (Get-Date).ToUniversalTime().ToString("o")
$prevState = @{}
if (Test-Path -LiteralPath $statePath) {
    try {
        $j = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $j.PSObject.Properties | ForEach-Object { $prevState[$_.Name] = $_.Value }
    } catch { $prevState = @{} }
}
$stateOut = [ordered]@{}
foreach ($k in $prevState.Keys) { $stateOut[$k] = $prevState[$k] }
$stateOut["last_seen_signal_ids"] = $idsOut
$stateOut["last_success_utc"] = $now
$stateOut["last_error"] = $null
$stateOut["forward_last_src_path"] = $src
$stateOut["forward_last_dst_path"] = $dst
$stateOut["forward_last_appended"] = $appended
$stateOut["forward_source_line_count"] = ($srcLines | Where-Object { $_.Trim().Length -gt 0 }).Count
$stateOut["forward_dest_signal_id_count"] = $lastSeen.Keys.Count
($stateOut | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $statePath -Encoding UTF8

$statusOut = [ordered]@{
    phase = "forward_signals"
    ts_utc = $now
    appended = $appended
    skipped_duplicate = $skipped_duplicate
    skipped_wrong_account = $skipped_wrong_account
    skipped_bad_json = $skipped_bad_json
    src = $src
    dst = $dst
}
($statusOut | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $statusPath -Encoding UTF8

Write-Host ("FORWARD: appended={0} src={1} dst={2}" -f $appended, $src, $dst)
