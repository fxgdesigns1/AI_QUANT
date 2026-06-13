# FXG Windows - Install Canonical FTMO_Bridge_EA
# Copies EA to MT5 Experts, compiles if MetaEditor available.
# Run from repo root. Detects repo root via script location.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$bridgesRoot = Split-Path -Parent $sidecarRoot
$repoRoot = Split-Path -Parent $bridgesRoot

$eaSource = Join-Path $repoRoot "ea\FTMO_Bridge_EA.mq5"
if (-not (Test-Path $eaSource)) {
    Write-Host "FAIL: EA source not found at $eaSource" -ForegroundColor Red
    exit 1
}

# Discover MT5 Data Folder - try common paths
$mt5Terminal = "C:\Program Files\MetaTrader 5\terminal64.exe"
if (-not (Test-Path $mt5Terminal)) {
    Write-Host "FAIL: MT5 not found at $mt5Terminal" -ForegroundColor Red
    exit 1
}

$userProfile = [Environment]::GetFolderPath("UserProfile")
$termBase = Join-Path $userProfile "AppData\Roaming\MetaQuotes\Terminal"
$expertsPath = $null
if (Test-Path $termBase) {
    $instances = Get-ChildItem $termBase -Directory
    foreach ($d in $instances) {
        $exp = Join-Path $d.FullName "MQL5\Experts"
        if (Test-Path $exp) {
            $expertsPath = $exp
            break
        }
    }
}
if (-not $expertsPath) {
    Write-Host "FAIL: Could not find MT5 MQL5\Experts. Open MT5 -> File -> Open Data Folder, then run with -ExpertsPath <path>" -ForegroundColor Red
    exit 1
}

$destMq5 = Join-Path $expertsPath "FTMO_Bridge_EA.mq5"
Copy-Item $eaSource $destMq5 -Force
Write-Host "Copied FTMO_Bridge_EA.mq5 to $destMq5" -ForegroundColor Green

# Try compile via MetaEditor if available (same folder as terminal64.exe)
$mt5Dir = Split-Path $mt5Terminal -Parent
$metaEditor = Join-Path $mt5Dir "metaeditor64.exe"
if (Test-Path $metaEditor) {
    Write-Host "Compiling via MetaEditor..." -ForegroundColor Cyan
    & $metaEditor /compile:$destMq5 /log 2>&1 | Out-Null
    $ex5Path = $destMq5 -replace '\.mq5$', '.ex5'
    if (Test-Path $ex5Path) {
        Write-Host "Compiled: $ex5Path" -ForegroundColor Green
    } else {
        Write-Host "Compile may have failed. Open MetaEditor and compile FTMO_Bridge_EA.mq5 manually." -ForegroundColor Yellow
    }
} else {
    Write-Host "MetaEditor not found. Open MT5 -> Tools -> MetaQuotes Language Editor, compile FTMO_Bridge_EA.mq5" -ForegroundColor Yellow
}

Write-Host "PASS: EA installed. Attach to chart in MT5 Navigator -> Expert Advisors" -ForegroundColor Green
