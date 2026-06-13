# Phase 8X: run the Phase 8M 5950X worker loop until MaxJobs, MaxHours, or queue empty.
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [string]$LocalRoot = "C:\Users\gavin\fxg-research\research_worker",
    [string]$RepoRoot = "",
    [string]$GcloudExe = "",
    [int]$MaxJobs = 0,
    [int]$MaxHours = 0,
    [int]$SleepSecondsBetweenJobs = 5,
    [switch]$DryRun
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

$worker = Join-Path $RepoRoot "scripts\phase8m_5950x_research_worker.py"
if (-not (Test-Path $worker)) { throw "MISSING_WORKER_SCRIPT:$worker" }

$perfDir = Join-Path $RepoRoot "ARTIFACTS\performance"
if (-not (Test-Path $perfDir)) { New-Item -ItemType Directory -Path $perfDir -Force | Out-Null }

function Extract-JsonObject([string]$Text) {
    if (-not $Text) { throw "NO_OUTPUT" }
    $start = $Text.IndexOf("{")
    $end = $Text.LastIndexOf("}")
    if ($start -lt 0 -or $end -le $start) { throw "NO_JSON_OBJECT_FOUND" }
    $jsonText = $Text.Substring($start, ($end - $start + 1))
    return ($jsonText | ConvertFrom-Json -ErrorAction Stop)
}

function Get-AlphaListJsonText {
    $remoteCmd = "cd $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8m_list_research_jobs.py"
    $out = & $gc compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $remoteCmd 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "GCLOUD_SSH_LIST_JOBS_FAILED:$out" }
    return $out
}

function Write-Phase8xProgress {
    param(
        [string]$AlphaListPath,
        [string]$LastWorkerPath,
        [string]$StopReason
    )
    $args = @(
        (Join-Path $RepoRoot "scripts\phase8x_write_batch_progress.py"),
        "--repo-root", $RepoRoot,
        "--alpha-list-json", $AlphaListPath,
        "--stop-reason", $StopReason
    )
    if ($LastWorkerPath -and (Test-Path $LastWorkerPath)) {
        $args += "--last-worker-json", ("@" + $LastWorkerPath)
    }
    Write-Host ("RUN python phase8x_write_batch_progress.py " + $StopReason)
    & $py $args
    if ($LASTEXITCODE -ne 0) { throw "PHASE8X_WRITE_PROGRESS_FAILED" }
}

function Save-JsonLineFile([string]$Text, [string]$Path) {
    $start = $Text.IndexOf("{")
    $end = $Text.LastIndexOf("}")
    if ($start -lt 0 -or $end -le $start) { throw "NO_JSON_FOR_FILE" }
    $jsonText = $Text.Substring($start, ($end - $start + 1))
    # UTF-8 without BOM — Python json.load/read_text("utf-8") rejects BOM; utf-8-sig accepts either.
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $jsonText, $utf8NoBom)
}

$deadline = $null
if ($MaxHours -gt 0) { $deadline = (Get-Date).AddHours($MaxHours) }

$n = 0
$results = @()
$stopReason = "RUNNING"
$listPath = Join-Path $env:TEMP ("phase8x_alpha_list_" + [guid]::NewGuid().ToString("N") + ".json")
$rawList0 = Get-AlphaListJsonText
Save-JsonLineFile $rawList0 $listPath
Write-Phase8xProgress -AlphaListPath $listPath -LastWorkerPath $null -StopReason "WORKER_INIT"

while ($true) {
    if ($null -ne $deadline -and (Get-Date) -gt $deadline) {
        $stopReason = "MAX_HOURS"
        Write-Host "PHASE8X_WORKER_STOP_REASON=MAX_HOURS"
        break
    }
    if ($MaxJobs -gt 0 -and $n -ge $MaxJobs) {
        $stopReason = "MAX_JOBS"
        Write-Host "PHASE8X_WORKER_STOP_REASON=MAX_JOBS"
        break
    }

    $argList = @(
        $worker,
        "--project", $GcpProject,
        "--zone", $GcpZone,
        "--vm", $AlphaVm,
        "--alpha-repo", $AlphaRemoteRepo,
        "--local-root", $LocalRoot
    )
    if ($DryRun) { $argList += "--dry-run" }

    $raw = & $py $argList 2>&1 | Out-String
    $j = Extract-JsonObject $raw
    $results += $j

    $cyclePath = Join-Path $env:TEMP ("phase8x_worker_cycle_" + [guid]::NewGuid().ToString("N") + ".json")
    Save-JsonLineFile $raw $cyclePath

    $rawList = Get-AlphaListJsonText
    Save-JsonLineFile $rawList $listPath
    Write-Phase8xProgress -AlphaListPath $listPath -LastWorkerPath $cyclePath -StopReason "RUNNING"

    Remove-Item -LiteralPath $cyclePath -Force -ErrorAction SilentlyContinue

    if ($j.status -eq "NO_PENDING_JOBS") {
        $stopReason = "NO_PENDING_JOBS"
        Write-Host "PHASE8X_WORKER_STOP_REASON=NO_PENDING_JOBS"
        break
    }
    if ($DryRun) {
        $stopReason = "DRY_RUN_SINGLE_POLL"
        Write-Host "PHASE8X_WORKER_STOP_REASON=DRY_RUN_SINGLE_POLL"
        break
    }

    $n++
    Start-Sleep -Seconds $SleepSecondsBetweenJobs
}

$rawListFinal = Get-AlphaListJsonText
Save-JsonLineFile $rawListFinal $listPath
Write-Phase8xProgress -AlphaListPath $listPath -LastWorkerPath $null -StopReason $stopReason
Remove-Item -LiteralPath $listPath -Force -ErrorAction SilentlyContinue

$summary = @{
    ok             = $true
    phase          = "Phase 8X"
    jobs_attempted = $n
    dry_run        = [bool]$DryRun
    last_payload   = $results[-1]
    stop_reason    = $stopReason
}
$summary | ConvertTo-Json -Depth 8 | Write-Host
