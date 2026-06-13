# FXG Windows - Reverse sync: active MT5 bridge log -> shared repo ftmo_bridge_log.jsonl.
# Append-only; dedupe key ts + type + signal_id + msg. Never writes MT5 file from repo.
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

function Get-BridgeDedupeKey {
    param([string]$Line)
    $t = $Line.Trim()
    if ($t.Length -eq 0) { return $null }
    try {
        $o = $t | ConvertFrom-Json
        $ts = if ($o.PSObject.Properties.Name -contains "ts") { [string]$o.ts } else { "" }
        $ty = if ($o.PSObject.Properties.Name -contains "type") { [string]$o.type } else { "" }
        $sid = if ($o.PSObject.Properties.Name -contains "signal_id") { [string]$o.signal_id } else { "" }
        $msg = if ($o.PSObject.Properties.Name -contains "msg") { [string]$o.msg } else { "" }
        return ($ts + "|" + $ty + "|" + $sid + "|" + $msg)
    } catch {
        return $null
    }
}

function Read-BridgeKeysFromFile {
    param([string]$Path, [System.Text.UTF8Encoding]$Utf8)
    $keys = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $keys }
    $lines = [System.IO.File]::ReadAllLines($Path, $Utf8)
    if ($null -eq $lines) { return $keys }
    foreach ($line in $lines) {
        $k = Get-BridgeDedupeKey -Line $line
        if ($k) { $keys[$k] = $true }
    }
    return $keys
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Get-FxgRepoRoot -ScriptDir $scriptDir
if ($env:FXG_REPO_ROOT -and (Test-Path -LiteralPath $env:FXG_REPO_ROOT)) { $repoRoot = $env:FXG_REPO_ROOT }

$dst = Join-Path $repoRoot "logs\ftmo_bridge_log.jsonl"
$mt5Files = Resolve-Mt5FilesDir -Override $null
if (-not $mt5Files) { throw "FAIL: Could not resolve MT5 MQL5\Files directory. Set FXG_MT5_FILES_DIR." }
$src = Join-Path $mt5Files "ftmo_bridge_log.jsonl"

$artifacts = Join-Path $repoRoot "artifacts"
if (-not (Test-Path -LiteralPath $artifacts)) { New-Item -ItemType Directory -Path $artifacts -Force | Out-Null }
$statePath = Join-Path $artifacts "windows_transport_state.json"

$utf8 = Get-FxgUtf8NoBom

if (-not (Test-Path -LiteralPath $dst)) {
    [System.IO.File]::WriteAllText($dst, "", $utf8)
}
if (-not (Test-Path -LiteralPath $src)) {
    [System.IO.File]::WriteAllText($src, "", $utf8)
}

$seenInRepo = Read-BridgeKeysFromFile -Path $dst -Utf8 $utf8

$stateObj = $null
if (Test-Path -LiteralPath $statePath) {
    try { $stateObj = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $stateObj = $null }
}
if ($stateObj -and $stateObj.PSObject.Properties.Name -contains "last_seen_bridge_keys") {
    $raw = $stateObj.last_seen_bridge_keys
    if ($null -ne $raw) {
        if ($raw -is [System.Array]) {
            foreach ($x in $raw) { if ($x) { $seenInRepo[[string]$x] = $true } }
        } else {
            $seenInRepo[[string]$raw] = $true
        }
    }
}

$srcLines = [System.IO.File]::ReadAllLines($src, $utf8)
$appended = 0
$skipped_duplicate = 0
$skipped_bad = 0

foreach ($line in $srcLines) {
    $t = $line.Trim()
    if ($t.Length -eq 0) { continue }
    $k = Get-BridgeDedupeKey -Line $t
    if (-not $k) { $skipped_bad++; continue }
    if ($seenInRepo.ContainsKey($k)) { $skipped_duplicate++; continue }
    $lineToWrite = $t
    if (-not $lineToWrite.EndsWith("`n")) {
        [System.IO.File]::AppendAllText($dst, $lineToWrite + "`n", $utf8)
    } else {
        [System.IO.File]::AppendAllText($dst, $lineToWrite, $utf8)
    }
    $seenInRepo[$k] = $true
    $appended++
}

$keyList = @($seenInRepo.Keys | Sort-Object)
$now = (Get-Date).ToUniversalTime().ToString("o")

$merged = [ordered]@{}
if (Test-Path -LiteralPath $statePath) {
    try {
        $j = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $j.PSObject.Properties | ForEach-Object { $merged[$_.Name] = $_.Value }
    } catch { }
}
$merged["last_seen_bridge_keys"] = $keyList
$merged["reverse_last_success_utc"] = $now
$merged["reverse_last_error"] = $null
$merged["reverse_last_src_path"] = $src
$merged["reverse_last_dst_path"] = $dst
$merged["reverse_last_appended"] = $appended
$merged["reverse_source_line_count"] = ($srcLines | Where-Object { $_.Trim().Length -gt 0 }).Count
$merged["reverse_dest_key_count"] = $seenInRepo.Keys.Count

($merged | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $statePath -Encoding UTF8

Write-Host ("REVERSE: appended={0} src={1} dst={2}" -f $appended, $src, $dst)
