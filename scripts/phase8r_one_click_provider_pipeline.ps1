# Phase 8R: verify provider keys (no secret echo), then Phase 8O exact replay, Phase 8P dashboard dry-run plan.
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [string]$EnvFile = ".secrets\phase8r_providers.env",
    [string]$Instrument = "EUR_USD",
    [int]$LookbackDays = 90,
    [int]$CalendarMaxCalls = 50,
    [string]$CapabilityProvider = "",
    [string]$Granularity = "M15",
    [string]$SessionBucket = "NY_OPEN_SECONDARY_PROPOSED",
    [switch]$SkipTests,
    [switch]$SkipPhase8O,
    [switch]$SkipPhase8P,
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$PerfDir = Join-Path $RepoRoot "ARTIFACTS\performance"
New-Item -ItemType Directory -Force -Path $PerfDir | Out-Null

function Write-Step([string]$msg) {
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

Write-Step "Phase 8R one-click: repo=$RepoRoot"

if (-not $SkipTests) {
    Write-Step "Unit tests (test_phase8*)"
    Push-Location $RepoRoot
    try {
        python -m unittest discover -s tests -p "test_phase8*.py" -v
        if ($LASTEXITCODE -ne 0) { throw "LOCAL_TESTS_FAILED" }
    } finally {
        Pop-Location
    }
}

$envPath = Join-Path $RepoRoot $EnvFile
Write-Step "Provider capability (secrets redacted; presence/counts only in JSON)"
$capArgs = @(
    (Join-Path $RepoRoot "scripts\phase8r_provider_capability.py"),
    "--instrument", $Instrument,
    "--lookback-days", "$LookbackDays",
    "--max-calendar-paid-calls", "$CalendarMaxCalls",
    "--output-dir", $PerfDir
)
if ($CapabilityProvider -ne "") {
    $capArgs += @("--provider", $CapabilityProvider)
} elseif ($CalendarMaxCalls -le 1) {
    # Budget 1 cannot probe every legacy calendar path first; target RapidAPI calendar only.
    $capArgs += @("--provider", "rapidapi_calendar")
}
if (Test-Path $envPath) {
    $capArgs += @("--env-file", $envPath)
} else {
    Write-Host "WARN: env file missing at $envPath - using process environment only." -ForegroundColor Yellow
}

python @capArgs
$capExit = $LASTEXITCODE
if ($capExit -ne 0) {
    Write-Host "PHASE8R_PROVIDER_CAPABILITY_FAIL_CLOSED (exit $capExit)" -ForegroundColor Red
    Write-Host "Skipping Phase 8O and Phase 8P until news+calendar providers verify with rows."
    exit $capExit
}

if (-not $SkipPhase8O) {
    Write-Step "Phase 8O one-click exact replay"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\phase8o_one_click_exact_replay.ps1") `
        -GcpProject $GcpProject -GcpZone $GcpZone -AlphaVm $AlphaVm -AlphaRemoteRepo $AlphaRemoteRepo `
        -Instrument $Instrument -Granularity $Granularity -LookbackDays $LookbackDays -SessionBucket $SessionBucket `
        -RepoRoot $RepoRoot -SkipTests
    if ($LASTEXITCODE -ne 0) { throw "PHASE8O_ONE_CLICK_FAILED" }
}

if (-not $SkipPhase8P) {
    Write-Step "Phase 8P weekend research cycle (DryRun + weekday allowance)"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\phase8p_weekend_research_cycle.ps1") `
        -GcpProject $GcpProject -GcpZone $GcpZone -AlphaVm $AlphaVm -AlphaRemoteRepo $AlphaRemoteRepo `
        -DryRun -AllowWeekdayApiPull -SkipTests
    if ($LASTEXITCODE -ne 0) { throw "PHASE8P_DRY_RUN_FAILED" }
}

Write-Host "PHASE8R_PIPELINE_COMPLETE" -ForegroundColor Green
exit 0
