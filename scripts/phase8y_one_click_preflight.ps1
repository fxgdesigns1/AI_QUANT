# Phase 8Y: one-click data coverage + API cost + context pack preflight.
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$Instrument = "EUR_USD",
    [int]$LookbackDays = 90,
    [switch]$DryRun,
    [switch]$BuildContextPack,
    [int]$MaxPaidCalendarCalls = 1,
    [switch]$AllowMissingNews,
    [switch]$AllowMissingCalendar,
    [switch]$RequireMacro
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot -or $RepoRoot -eq "") {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw "MISSING_PYTHON_ON_PATH" }

function Invoke-PyScript([string]$RelScript, [string[]]$ScriptArgs) {
    $script = Join-Path $RepoRoot $RelScript
    $full = @($script) + $ScriptArgs
    Write-Host ("RUN " + ($full -join " "))
    & $py $full
    if ($LASTEXITCODE -ne 0) { throw "PYTHON_FAILED:$RelScript" }
}

function Read-Json([string]$PathText) {
    if (-not (Test-Path $PathText)) { return $null }
    return (Get-Content $PathText -Raw | ConvertFrom-Json)
}

$perf = Join-Path $RepoRoot "ARTIFACTS\performance"
$coveragePath = Join-Path $perf "latest_phase8y_data_coverage_manifest.json"
$costPath = Join-Path $perf "latest_phase8y_api_cost_estimate.json"
$packManifestPath = Join-Path $perf "latest_phase8y_shared_context_pack_manifest.json"
$verifyPath = Join-Path $perf "latest_phase8y_context_pack_verification.json"

$invArgs = @(
    "--repo-root", $RepoRoot,
    "--instrument", $Instrument,
    "--lookback-days", "$LookbackDays",
    "--max-paid-calendar-calls", "$MaxPaidCalendarCalls",
    "--output", $coveragePath
)
if (-not $AllowMissingNews) { $invArgs += "--require-news" }
if (-not $AllowMissingCalendar) { $invArgs += "--require-calendar" }
if ($RequireMacro) { $invArgs += "--require-macro" }
if ($DryRun) { $invArgs += "--dry-run" }
Invoke-PyScript "scripts\phase8y_inventory_data_coverage.py" $invArgs

if ($DryRun) {
    # Write concrete artifacts even in dry-run mode; the scripts remain no-network/no-paid-call.
    $writeArgs = @($invArgs | Where-Object { $_ -ne "--dry-run" })
    Invoke-PyScript "scripts\phase8y_inventory_data_coverage.py" $writeArgs
}

Invoke-PyScript "scripts\phase8y_estimate_api_cost.py" @(
    "--repo-root", $RepoRoot,
    "--manifest", $coveragePath,
    "--output", $costPath,
    "--max-paid-calendar-calls", "$MaxPaidCalendarCalls"
)

$coverage = Read-Json $coveragePath
$cost = Read-Json $costPath

if ($BuildContextPack) {
    Invoke-PyScript "scripts\phase8y_build_shared_context_pack.py" @(
        "--repo-root", $RepoRoot,
        "--coverage-manifest", $coveragePath,
        "--cost-estimate", $costPath,
        "--manifest-output", $packManifestPath
    )
    Invoke-PyScript "scripts\phase8y_verify_context_pack.py" @(
        "--repo-root", $RepoRoot,
        "--manifest", $packManifestPath,
        "--output", $verifyPath
    )
}

$verify = Read-Json $verifyPath
$safe = $false
if ($coverage -and $cost) {
    $safe = [bool]$coverage.safe_to_run_batch -and [bool]$cost.safe_to_run_batch
}
if ($BuildContextPack) {
    $safe = $safe -and [bool]($verify -and $verify.all_files_verified -eq $true)
}

$out = @{
    ok = $true
    phase = "Phase 8Y"
    classification = $(if ($safe) { "PASS_DATA_COVERAGE_AND_API_COST_PREFLIGHT_READY" } else { "FAIL_CLOSED_DATA_COVERAGE_OR_BUDGET" })
    coverage_manifest = $coveragePath
    api_cost_estimate = $costPath
    context_pack_manifest = $(if ($BuildContextPack) { $packManifestPath } else { $null })
    context_pack_verification = $(if ($BuildContextPack) { $verifyPath } else { $null })
    dry_run = [bool]$DryRun
    safe_to_run_batch = [bool]$safe
    estimated_calls_needed = $(if ($coverage) { [int]$coverage.estimated_api_calls_needed } else { $null })
    estimated_paid_calendar_calls_needed = $(if ($coverage) { [int]$coverage.estimated_paid_calendar_calls_needed } else { $null })
    monthly_calendar_calls_used = $(if ($coverage) { [int]$coverage.monthly_calendar_calls_used } else { $null })
    monthly_calendar_calls_remaining = $(if ($coverage) { [int]$coverage.monthly_calendar_calls_remaining } else { $null })
    no_paid_calls_spent_in_dry_run = [bool]$DryRun
    ny_live_enabled = $false
    execution_paths_changed = $false
}

$json = ($out | ConvertTo-Json -Depth 8)
Write-Host $json
if (-not $safe) { exit 2 }
exit 0
