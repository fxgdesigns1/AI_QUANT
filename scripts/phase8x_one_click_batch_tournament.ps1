# Phase 8X: one-click batch tournament — queue (ALPHA), optional worker cycles, score, leaderboard, dashboard.
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [string]$LocalRoot = "C:\Users\gavin\fxg-research\research_worker",
    [int]$MaxJobs = 0,
    [int]$MaxHours = 0,
    [switch]$DryRun,
    [switch]$SkipCreate,
    [switch]$SkipWorker,
    [switch]$SkipDashboard,
    [int]$CalendarApiMaxCalls = 3,
    [switch]$SkipCalendarPreflight,
    [switch]$SkipPhase8YPreflight,
    [switch]$CreateJobsOnAlpha,
    [string]$GcloudExe = ""
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot -or $RepoRoot -eq "") {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw "MISSING_PYTHON_ON_PATH" }

$gc = $GcloudExe
if (-not $gc) { $gc = $env:GCLOUD_PATH }
if (-not $gc) { $gc = "gcloud" }

function Invoke-PyScript([string]$RelScript, [string[]]$ScriptArgs) {
    $script = Join-Path $RepoRoot $RelScript
    $full = @($script) + $ScriptArgs
    Write-Host ("RUN " + ($full -join " "))
    & $py $full
    if ($LASTEXITCODE -ne 0) { throw "PYTHON_FAILED:$RelScript" }
}

function Invoke-PyCapture([string]$RelScript, [string[]]$ScriptArgs) {
    $script = Join-Path $RepoRoot $RelScript
    $full = @($script) + $ScriptArgs
    Write-Host ("RUN " + ($full -join " "))
    $out = & $py $full 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "PYTHON_FAILED:$RelScript" }
    return $out
}

function Extract-JsonObject([string]$Text) {
    if (-not $Text) { throw "NO_OUTPUT" }
    $start = $Text.IndexOf("{")
    $end = $Text.LastIndexOf("}")
    if ($start -lt 0 -or $end -le $start) { throw "NO_JSON_OBJECT_FOUND" }
    $jsonText = $Text.Substring($start, ($end - $start + 1))
    return ($jsonText | ConvertFrom-Json -ErrorAction Stop)
}

function Get-AlphaResearchJobsRaw {
    param(
        [string]$Project,
        [string]$Zone,
        [string]$Vm,
        [string]$AlphaRepo
    )
    $remoteCmd = "cd $AlphaRepo && sudo -u aiquant $AlphaRepo/.venv/bin/python3 scripts/phase8m_list_research_jobs.py"
    Write-Host "RUN gcloud compute ssh ... list_research_jobs"
    $out = & $gc compute ssh --zone $Zone --project $Project $Vm --command $remoteCmd 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "GCLOUD_SSH_LIST_JOBS_FAILED:$out" }
    return $out
}

if ($CreateJobsOnAlpha -and -not $DryRun) {
    if ($MaxJobs -le 0) { throw "CreateJobsOnAlpha_requires_MaxJobs_gt_0" }
    if ($SkipCreate) { throw "CreateJobsOnAlpha_conflicts_with_SkipCreate" }
}

# 1) Create batch (dry-run prints exact job count only)
$createArgs = @(
    "--repo-root", $RepoRoot,
    "--calendar-api-max-calls", "$CalendarApiMaxCalls"
)
if ($DryRun) { $createArgs += "--dry-run" }
if ($SkipCalendarPreflight) { $createArgs += "--skip-calendar-preflight" }
if ($SkipPhase8YPreflight) { $createArgs += "--skip-phase8y-preflight" }
if ($MaxJobs -gt 0) { $createArgs += "--max-jobs", "$MaxJobs" }

if (-not $SkipCreate) {
    if ($CreateJobsOnAlpha -and -not $DryRun) {
        $perfDirForManifest = Join-Path $RepoRoot "ARTIFACTS\performance"
        if (-not (Test-Path $perfDirForManifest)) { New-Item -ItemType Directory -Force -Path $perfDirForManifest | Out-Null }
        $targetManifestPath = Join-Path $RepoRoot "ARTIFACTS\performance\phase8x_active_batch_target.json"
        $targetManifestForPy = [System.IO.Path]::GetFullPath($targetManifestPath).Replace("\", "/")

        $beforeRaw = Get-AlphaResearchJobsRaw -Project $GcpProject -Zone $GcpZone -Vm $AlphaVm -AlphaRepo $AlphaRemoteRepo
        $before = Extract-JsonObject $beforeRaw
        $pendingBefore = [int]$before.counts.pending

        $stagingRoot = Join-Path $env:TEMP ("phase8x_alpha_staging_" + [guid]::NewGuid().ToString("N"))
        $jobRootStaging = Join-Path $stagingRoot "ARTIFACTS\research_jobs"
        New-Item -ItemType Directory -Path $jobRootStaging -Force | Out-Null
        $jobRootForPy = ($jobRootStaging | Resolve-Path).Path.Replace("\", "/")

        $createRemote = @(
            "--repo-root", $RepoRoot,
            "--job-root", $jobRootForPy,
            "--target-manifest-out", $targetManifestForPy,
            "--calendar-api-max-calls", "$CalendarApiMaxCalls"
        )
        if ($SkipCalendarPreflight) { $createRemote += "--skip-calendar-preflight" }
        if ($SkipPhase8YPreflight) { $createRemote += "--skip-phase8y-preflight" }
        if ($MaxJobs -gt 0) { $createRemote += "--max-jobs", "$MaxJobs" }

        $createOut = Invoke-PyCapture "scripts\phase8x_create_batch_jobs.py" $createRemote
        $createJson = Extract-JsonObject $createOut
        if (-not $createJson.ok) { throw "CREATE_JOBS_FAILED" }
        $createdCount = [int]$createJson.created

        $pendingDir = Join-Path $jobRootStaging "queue\pending"
        $jsonFiles = @(Get-ChildItem -Path $pendingDir -Filter "*.json" -File -ErrorAction SilentlyContinue)
        if ($jsonFiles.Count -ne $createdCount) { throw "STAGING_PENDING_COUNT_MISMATCH" }

        $tarName = "phase8x_pending_" + [guid]::NewGuid().ToString("N") + ".tar.gz"
        $tarLocal = Join-Path $env:TEMP $tarName
        Push-Location $stagingRoot
        try {
            $tarBin = (Get-Command tar -ErrorAction SilentlyContinue).Source
            if (-not $tarBin) { throw "MISSING_TAR_EXE" }
            & $tarBin -czf $tarLocal "ARTIFACTS/research_jobs/queue/pending"
            if ($LASTEXITCODE -ne 0) { throw "TAR_CREATE_FAILED" }
        } finally {
            Pop-Location
        }

        $remoteTar = "/tmp/$tarName"
        Write-Host "RUN gcloud compute scp bundle -> ${AlphaVm}:$remoteTar"
        & $gc compute scp --zone $GcpZone --project $GcpProject $tarLocal "${AlphaVm}:$remoteTar"
        if ($LASTEXITCODE -ne 0) { throw "GCLOUD_SCP_FAILED" }

        $deploySh = @'
#!/bin/bash
set -euo pipefail
BUNDLE="__BUNDLE__"
EX="/tmp/phase8x_extract_${RANDOM}"
sudo rm -rf "$EX"
sudo mkdir -p "$EX"
sudo tar -xzf "$BUNDLE" -C "$EX"
SRC="$EX/ARTIFACTS/research_jobs/queue/pending"
DST="/opt/ai-quant/ARTIFACTS/research_jobs/queue/pending"
if [ ! -d "$SRC" ]; then echo "MISSING_SRC_PENDING_DIR" >&2; exit 2; fi
sudo mkdir -p "$DST"
shopt -s nullglob
for f in "$SRC"/*.json; do
  bn=$(basename "$f")
  if [ -f "$DST/$bn" ]; then echo "DUPLICATE_PENDING_JOB:$bn" >&2; exit 3; fi
done
for f in "$SRC"/*.json; do
  bn=$(basename "$f")
  sudo cp "$f" "$DST/$bn"
  sudo chown aiquant:aiquant "$DST/$bn"
done
rm -f "$BUNDLE" || true
rm -f /tmp/phase8x_deploy_pending.sh || true
echo "PHASE8X_ALPHA_DEPLOY_OK"
'@
        $deploySh = $deploySh.Replace("__BUNDLE__", $remoteTar)
        $deployLocal = Join-Path $env:TEMP ("phase8x_deploy_" + [guid]::NewGuid().ToString("N") + ".sh")
        Set-Content -LiteralPath $deployLocal -Value $deploySh -Encoding utf8
        $remoteDeploySh = "/tmp/phase8x_deploy_pending.sh"
        & $gc compute scp --zone $GcpZone --project $GcpProject $deployLocal "${AlphaVm}:$remoteDeploySh"
        if ($LASTEXITCODE -ne 0) { throw "GCLOUD_SCP_DEPLOY_SCRIPT_FAILED" }
        Write-Host "RUN gcloud compute ssh ... deploy_pending_bundle"
        $depOut = & $gc compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "chmod +x $remoteDeploySh && bash $remoteDeploySh" 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { throw "ALPHA_DEPLOY_FAILED:$depOut" }
        Remove-Item -LiteralPath $deployLocal -Force -ErrorAction SilentlyContinue

        $afterRaw = Get-AlphaResearchJobsRaw -Project $GcpProject -Zone $GcpZone -Vm $AlphaVm -AlphaRepo $AlphaRemoteRepo
        $after = Extract-JsonObject $afterRaw
        $pendingAfter = [int]$after.counts.pending
        $delta = $pendingAfter - $pendingBefore
        if ($delta -lt $createdCount) {
            throw "ALPHA_PENDING_DID_NOT_INCREASE_FAIL_CLOSED:before=$pendingBefore after=$pendingAfter created=$createdCount delta=$delta"
        }

        Remove-Item -LiteralPath $tarLocal -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force -ErrorAction SilentlyContinue

        Write-Host "PHASE8X_CREATE_JOBS_ON_ALPHA_OK pending_before=$pendingBefore pending_after=$pendingAfter created=$createdCount"
    }
    else {
        Invoke-PyScript "scripts\phase8x_create_batch_jobs.py" $createArgs
    }
}

if ($DryRun) {
    Write-Host "PHASE8X_ONE_CLICK_COMPLETE_DRY_RUN"
    exit 0
}

# 2) Worker (5950X / local PC — heavy work; never on ALPHA)
if (-not $SkipWorker) {
    $effMaxJobs = $MaxJobs
    $effMaxHours = $MaxHours
    if ($effMaxJobs -eq 0 -and $effMaxHours -eq 0) {
        $effMaxJobs = 1
    }
    $workerPs1 = Join-Path $RepoRoot "scripts\phase8x_run_batch_worker.ps1"
    $wArgs = @(
        "-GcpProject", $GcpProject,
        "-GcpZone", $GcpZone,
        "-AlphaVm", $AlphaVm,
        "-AlphaRemoteRepo", $AlphaRemoteRepo,
        "-LocalRoot", $LocalRoot,
        "-RepoRoot", $RepoRoot,
        "-GcloudExe", $gc
    )
    if ($effMaxJobs -gt 0) { $wArgs += "-MaxJobs", "$effMaxJobs" }
    if ($effMaxHours -gt 0) { $wArgs += "-MaxHours", "$effMaxHours" }
    powershell -ExecutionPolicy Bypass -File $workerPs1 @wArgs
}

# 3) Score + leaderboard + dashboard
Invoke-PyScript "scripts\phase8x_score_batch_results.py" @("--repo-root", $RepoRoot)
Invoke-PyScript "scripts\phase8x_build_tournament_leaderboard.py" @("--repo-root", $RepoRoot)

if (-not $SkipDashboard) {
    Invoke-PyScript "scripts\phase8p_build_research_dashboard.py" @("--repo-root", $RepoRoot)
}

Write-Host "PHASE8X_ONE_CLICK_BATCH_TOURNAMENT_DONE"
exit 0
