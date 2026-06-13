# FXG Windows - Inject One Test Signal for EA Verification
# Appends a single paper test signal to signals_ftmo_demo2.jsonl in MT5 Files.
# Run AFTER EA is attached. Use only for verification; producer normally writes.
param(
    [ValidateSet("MARKET", "LIMIT")]
    [string]$EntryType = "MARKET",
    [double]$EntryPrice = 0
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir)))

$userProfile = [Environment]::GetFolderPath("UserProfile")
$termBase = Join-Path $userProfile "AppData\Roaming\MetaQuotes\Terminal"
$signalFile = $null
foreach ($d in (Get-ChildItem $termBase -Directory)) {
    $fp = Join-Path $d.FullName "MQL5\Files\signals_ftmo_demo2.jsonl"
    if (Test-Path $fp) { $signalFile = $fp; break }
}
if (-not $signalFile) {
    Write-Host "FAIL: signals_ftmo_demo2.jsonl not found. Run fxg_win_wire_canonical_signals.ps1 first." -ForegroundColor Red
    exit 1
}

$signalId = "test_" + (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
$payload = @{
    signal_id = $signalId
    strategy = "MANUAL_010_TEST"
    symbol = "EUR_USD"
    side = "BUY"
    units = 1000
    entry_type = $EntryType
    stop_loss = $null
    take_profit = $null
    confidence = 0.5
    regime = "test"
    session = "test"
    news_state = "none"
    execution_allowed = $true
    block_reason = $null
    account = "010"
    bridge_account = "ftmo_demo2"
}
if ($EntryType -eq "LIMIT") {
    if ($EntryPrice -le 0) {
        Write-Host "FAIL: LIMIT requires -EntryPrice > 0 (e.g. a BuyLimit price below current Ask)." -ForegroundColor Red
        exit 1
    }
    $payload["entry_price"] = $EntryPrice
}
$line = $payload | ConvertTo-Json -Compress
Add-Content -Path $signalFile -Value $line -Encoding UTF8
Write-Host "Injected test signal: $signalId" -ForegroundColor Green
Write-Host "EA should consume within ~2 seconds. Check Experts tab and ftmo_bridge_log.jsonl" -ForegroundColor Cyan
