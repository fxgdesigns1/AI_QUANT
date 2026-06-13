# FXG Windows - Probe MT5 Terminal Identity and Symbol Truth
# Phase 1 verification: terminal path, account, Market Watch symbols, EURUSD probe.
# Outputs: artifacts/windows_mt5_terminal_identity.json, windows_marketwatch_selected_symbols.json, windows_symbol_name_probe.json

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$repoRoot = (Get-Item $sidecarRoot).Parent.Parent.FullName
$artifactsDir = Join-Path $repoRoot "artifacts"
if (-not (Test-Path $artifactsDir)) { New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null }

# Load .env for MT5_TERMINAL_PATH
$envFile = Join-Path $sidecarRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

$venvPython = Join-Path $sidecarRoot "venv\Scripts\python.exe"
$probeScript = Join-Path $scriptDir "probe_mt5_symbols.py"
if (-not (Test-Path $probeScript)) {
    Write-Host "FAIL: probe_mt5_symbols.py not found" -ForegroundColor Red
    exit 1
}
$py = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "Running MT5 probe..." -ForegroundColor Cyan
$out = & $py $probeScript 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host $out -ForegroundColor Red
    exit 1
}
$json = $out | ConvertFrom-Json

# Extract slices for Phase 1 artifacts
$terminalIdentity = @{
    initialize_ok = $json.initialize_ok
    terminal_path = $json.terminal_path
    terminal_info = $json.terminal_info
    account_info = $json.account_info
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 5

$marketwatch = @{
    symbols_total = $json.symbols_total
    symbols_total_selected = $json.symbols_total_selected
    selected_symbols_sample = $json.selected_symbols_sample
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 3

$symbolProbe = @{
    eurusd_probe = $json.eurusd_probe
    eurusd_like_symbols = $json.eurusd_like_symbols
    last_error = $json.last_error
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 5

$terminalIdentity | Set-Content (Join-Path $artifactsDir "windows_mt5_terminal_identity.json") -Encoding UTF8
$marketwatch | Set-Content (Join-Path $artifactsDir "windows_marketwatch_selected_symbols.json") -Encoding UTF8
$symbolProbe | Set-Content (Join-Path $artifactsDir "windows_symbol_name_probe.json") -Encoding UTF8

Write-Host "Artifacts written to $artifactsDir" -ForegroundColor Green
Write-Host "  windows_mt5_terminal_identity.json" -ForegroundColor Gray
Write-Host "  windows_marketwatch_selected_symbols.json" -ForegroundColor Gray
Write-Host "  windows_symbol_name_probe.json" -ForegroundColor Gray
