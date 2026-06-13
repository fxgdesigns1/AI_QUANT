# FXG Windows - Wire Canonical Signal Files to MT5
# Creates signals_ftmo_demo2.jsonl and ftmo_bridge_log.jsonl in MT5 MQL5/Files.
# The producer (Mac/ALPHA) writes to its path; sync or copy must deliver to this folder.
# Run from repo root.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir)))

$userProfile = [Environment]::GetFolderPath("UserProfile")
$termBase = Join-Path $userProfile "AppData\Roaming\MetaQuotes\Terminal"
$filesPath = $null
# Prefer the data folder for the *running* terminal64.exe (origin.txt must match install dir).
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
            $mql5 = Join-Path $d.FullName "MQL5"
            if (-not (Test-Path $mql5)) { continue }
            $fp = Join-Path $d.FullName "MQL5\Files"
            if (-not (Test-Path $fp)) { New-Item -ItemType Directory -Path $fp -Force | Out-Null }
            $filesPath = $fp
            break
        }
    }
    if (-not $filesPath) {
        foreach ($d in (Get-ChildItem $termBase -Directory)) {
            $fp = Join-Path $d.FullName "MQL5\Files"
            if (Test-Path (Join-Path $d.FullName "MQL5")) {
                if (-not (Test-Path $fp)) { New-Item -ItemType Directory -Path $fp -Force | Out-Null }
                $filesPath = $fp
                break
            }
        }
    }
}
if (-not $filesPath) {
    Write-Host "FAIL: Could not find MT5 MQL5\Files" -ForegroundColor Red
    exit 1
}

$signalFile = Join-Path $filesPath "signals_ftmo_demo2.jsonl"
$bridgeLog = Join-Path $filesPath "ftmo_bridge_log.jsonl"

# Ensure files exist (empty if new)
if (-not (Test-Path $signalFile)) {
    "" | Set-Content $signalFile -Encoding UTF8
    Write-Host "Created $signalFile" -ForegroundColor Cyan
}
if (-not (Test-Path $bridgeLog)) {
    "" | Set-Content $bridgeLog -Encoding UTF8
    Write-Host "Created $bridgeLog" -ForegroundColor Cyan
}

# If sync source exists (e.g. repo or shared drive), create junction
$repoSignals = Join-Path $repoRoot "signals_ftmo_demo2.jsonl"
if ((Test-Path $repoSignals) -and (-not (Get-Item $signalFile).Length -gt 0)) {
    Write-Host "Repo signal file exists. For live sync, configure your sync tool to copy to $filesPath" -ForegroundColor Yellow
}

Write-Host "MT5 Files path: $filesPath" -ForegroundColor Green
Write-Host "Signal file: $signalFile" -ForegroundColor Gray
Write-Host "Bridge log: $bridgeLog" -ForegroundColor Gray
Write-Host "PASS: Wiring ready. Producer must write/sync to this path." -ForegroundColor Green
