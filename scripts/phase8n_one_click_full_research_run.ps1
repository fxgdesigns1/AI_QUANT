# Phase 8N: one-click full research cycle runner (PC/5950X).
# Creates a Phase 8M job on ALPHA, runs the 5950X worker cycle(s), verifies ALPHA readback,
# prints final metrics and MacBook pull commands, and writes a local final report JSON.

[CmdletBinding()]
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [ValidateSet("phase8l_backtest", "phase8k_replay")]
    [string]$JobType = "phase8l_backtest",
    [string]$Instrument = "EUR_USD",
    [string]$Granularity = "M15",
    [int]$LookbackDays = 90,
    [string]$SessionBucket = "NY_OPEN_SECONDARY_PROPOSED",
    [string]$SessionWindowUtc = "13:30-16:00",
    [int]$MaxWaitMinutes = 240,
    [int]$PollSeconds = 20,
    [int]$WorkerCyclesMax = 1,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

function Fail([string]$Msg) {
    Write-Host "PHASE8N_ONE_CLICK_FAILED"
    Write-Host $Msg
    exit 1
}

function Require-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) { Fail "MISSING_REQUIRED_COMMAND:$Name" }
    return $cmd.Source
}

function Extract-JsonObject([string]$Text) {
    if (-not $Text) { throw "NO_OUTPUT" }
    $start = $Text.IndexOf("{")
    $end = $Text.LastIndexOf("}")
    if ($start -lt 0 -or $end -le $start) { throw "NO_JSON_OBJECT_FOUND" }
    $jsonText = $Text.Substring($start, ($end - $start + 1))
    return ($jsonText | ConvertFrom-Json -ErrorAction Stop)
}

function Assert-NoBlockedKeywords {
    param([hashtable]$Params)
    $blocked = @("live", "trade_order", "order", "execution", "send_trade", "mt5_signal", "enable_live", "lane_change")
    foreach ($k in $Params.Keys) {
        $v = [string]$Params[$k]
        foreach ($b in $blocked) {
            if ($v.ToLower().Contains($b)) {
                throw "BLOCKED_KEYWORD_IN_PARAM:${k}:${b}"
            }
        }
    }
}

function Gcloud-Ssh([string]$RemoteCommand) {
    $cmd = @(
        "compute", "ssh",
        "--quiet",
        "--zone", $GcpZone,
        "--project", $GcpProject,
        $AlphaVm,
        "--command", $RemoteCommand
    )
    $out = & gcloud @cmd 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "GCLOUD_SSH_FAILED:`n$out"
    }
    return ($out | Out-String)
}

function Gcloud-Scp([string]$Remote, [string]$Local) {
    $cmd = @(
        "compute", "scp",
        "--quiet",
        "--zone", $GcpZone,
        "--project", $GcpProject,
        $Remote,
        $Local
    )
    $out = & gcloud @cmd 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "GCLOUD_SCP_FAILED:`n$out"
    }
    return ($out | Out-String)
}

$startedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactsDir = Join-Path $repoRoot "artifacts"
New-Item -ItemType Directory -Force -Path $artifactsDir | Out-Null
$ts = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$localLatestJson = Join-Path $artifactsDir "PHASE8N_latest_research_job_result_$ts.json"
$localFinalReport = Join-Path $artifactsDir "PHASE8N_ONE_CLICK_FINAL_REPORT_$ts.json"

try {
    Require-Command "gcloud" | Out-Null
    Require-Command "powershell" | Out-Null
} catch {
    Fail $_.Exception.Message
}

try {
    Assert-NoBlockedKeywords -Params @{
        "JobType" = $JobType
        "Instrument" = $Instrument
        "Granularity" = $Granularity
        "SessionBucket" = $SessionBucket
        "SessionWindowUtc" = $SessionWindowUtc
    }
} catch {
    Fail $_.Exception.Message
}

try {
    # Connectivity proof (no heavy work on ALPHA).
    $ping = Gcloud-Ssh "echo PHASE8N_ALPHA_OK"
    if (-not $ping.Contains("PHASE8N_ALPHA_OK")) { throw "ALPHA_CONNECTIVITY_UNCONFIRMED" }

    # Verify Phase 8M scripts exist on ALPHA (fail closed).
    $verifyScriptsCmd = "cd $AlphaRemoteRepo && test -f scripts/phase8m_create_research_job.py -a -f scripts/phase8m_list_research_jobs.py -a -f scripts/phase8m_import_research_result.py && echo PHASE8N_ALPHA_SCRIPTS_OK"
    $verified = Gcloud-Ssh $verifyScriptsCmd
    if (-not $verified.Contains("PHASE8N_ALPHA_SCRIPTS_OK")) { throw "PHASE8M_SCRIPTS_MISSING_ON_ALPHA" }
} catch {
    Fail $_.Exception.Message
}

if (-not $SkipTests) {
    try {
        $python = $null
        foreach ($name in @("python", "python3")) {
            $c = Get-Command $name -ErrorAction SilentlyContinue
            if ($c -and $c.Source) { $python = $c.Source; break }
        }
        if (-not $python) {
            $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
            if ($pyLauncher) {
                $resolved = & py -3 -c "import sys; print(sys.executable)" 2>$null
                if ($resolved) { $python = $resolved.Trim() }
            }
        }
        if (-not $python) { throw "NO_PYTHON_FOR_TESTS" }
        Write-Host "PHASE8N_RUNNING_TESTS python=$python"
        & $python -m unittest discover -s tests -p "test_phase8*.py" -v
        if ($LASTEXITCODE -ne 0) { throw "TESTS_FAILED" }
    } catch {
        Fail $_.Exception.Message
    }
}

$jobId = $null
$jobStatus = $null
$latestMetrics = $null
$alphaLatestPointer = "${AlphaVm}:${AlphaRemoteRepo}/ARTIFACTS/performance/latest_research_job_result.json"

try {
    # Create job on ALPHA (Phase 8M job queue).
    # IMPORTANT: pass a single-line command to bash; multi-line strings can break as separate shell commands.
    $remoteCreate = (
        "cd $AlphaRemoteRepo && " +
        "sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8m_create_research_job.py " +
        "--job-type $JobType " +
        "--instrument $Instrument " +
        "--granularity $Granularity " +
        "--lookback-days $LookbackDays " +
        "--session-bucket $SessionBucket " +
        "--session-window-utc $SessionWindowUtc"
    ).Trim()

    $createOut = Gcloud-Ssh $remoteCreate
    $createObj = Extract-JsonObject $createOut
    if (-not $createObj.ok) { throw "CREATE_JOB_NOT_OK:$($createOut.Trim())" }
    $jobId = [string]$createObj.job_id
    if (-not $jobId) { throw "MISSING_JOB_ID" }

    # Confirm it appears as PENDING.
    $remoteList = "cd $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8m_list_research_jobs.py"
    $listOut = Gcloud-Ssh $remoteList
    $listObj = Extract-JsonObject $listOut
    $pending = @($listObj.jobs.pending | Where-Object { $_.job_id -eq $jobId })
    if ($pending.Count -lt 1) { throw "JOB_NOT_FOUND_IN_PENDING:$jobId" }

    # Run local worker cycle(s) (heavy compute stays on this PC).
    $cycles = 0
    $deadline = (Get-Date).ToUniversalTime().AddMinutes([double]$MaxWaitMinutes)
    while ($true) {
        if ((Get-Date).ToUniversalTime() -gt $deadline) { throw "TIMEOUT_WAITING_FOR_JOB:$jobId" }

        if ($cycles -lt $WorkerCyclesMax) {
            Write-Host "PHASE8N_WORKER_CYCLE_START job_id=$jobId cycle=$($cycles+1)/$WorkerCyclesMax"
            & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "phase8m_worker_once.ps1") `
                -GcpProject $GcpProject -GcpZone $GcpZone -AlphaVm $AlphaVm -AlphaRemoteRepo $AlphaRemoteRepo -JobId $jobId
            if ($LASTEXITCODE -ne 0) { throw "WORKER_ONCE_FAILED" }
            $cycles += 1
        }

        $listOut2 = Gcloud-Ssh $remoteList
        $listObj2 = Extract-JsonObject $listOut2

        $foundDone = @($listObj2.jobs.done | Where-Object { $_.job_id -eq $jobId })
        $foundFail = @($listObj2.jobs.failed | Where-Object { $_.job_id -eq $jobId })
        $foundRun = @($listObj2.jobs.running | Where-Object { $_.job_id -eq $jobId })
        $foundPen = @($listObj2.jobs.pending | Where-Object { $_.job_id -eq $jobId })

        if ($foundDone.Count -ge 1) { $jobStatus = "DONE"; break }
        if ($foundFail.Count -ge 1) { $jobStatus = "FAILED"; break }
        if ($foundRun.Count -ge 1) { $jobStatus = "RUNNING" }
        elseif ($foundPen.Count -ge 1) { $jobStatus = "PENDING" }
        else { $jobStatus = "UNKNOWN" }

        if ($cycles -ge $WorkerCyclesMax) {
            Start-Sleep -Seconds $PollSeconds
        }
    }

    # Fetch latest ALPHA result pointer and validate it locally (fail-closed safety checks).
    Gcloud-Scp "${AlphaVm}:${AlphaRemoteRepo}/ARTIFACTS/performance/latest_research_job_result.json" $localLatestJson | Out-Null
    if (-not (Test-Path -LiteralPath $localLatestJson)) { throw "LATEST_RESULT_POINTER_NOT_DOWNLOADED" }

    $pyStatus = Join-Path $PSScriptRoot "phase8n_one_click_status.py"
    if (-not (Test-Path -LiteralPath $pyStatus)) { throw "MISSING_HELPER_SCRIPT:$pyStatus" }

    $pythonForStatus = $null
    foreach ($name in @("python", "python3")) {
        $c = Get-Command $name -ErrorAction SilentlyContinue
        if ($c -and $c.Source) { $pythonForStatus = $c.Source; break }
    }
    if (-not $pythonForStatus) {
        $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            $resolved = & py -3 -c "import sys; print(sys.executable)" 2>$null
            if ($resolved) { $pythonForStatus = $resolved.Trim() }
        }
    }
    if (-not $pythonForStatus) { throw "NO_PYTHON_FOR_STATUS_PARSER" }

    $statusOut = & $pythonForStatus $pyStatus --latest-json $localLatestJson 2>&1
    if ($LASTEXITCODE -ne 0) { throw "STATUS_PARSER_FAILED:`n$statusOut" }
    $latestMetrics = Extract-JsonObject ($statusOut | Out-String)

    # Enforce size cap (Phase 8M import manifest includes actual pack bytes).
    $packBytes = [int64]$latestMetrics.result_pack_size_bytes
    if ($packBytes -gt (25 * 1024 * 1024)) { throw "RESULT_PACK_TOO_LARGE_BYTES:$packBytes" }

    $finishedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $report = @{
        ok = $true
        phase = "Phase 8N"
        classification = "PHASE8N_ONE_CLICK_FINAL_REPORT"
        started_at_utc = $startedAtUtc
        finished_at_utc = $finishedAtUtc
        gcp = @{
            project = $GcpProject
            zone = $GcpZone
            alpha_vm = $AlphaVm
            alpha_repo = $AlphaRemoteRepo
        }
        request = @{
            job_type = $JobType
            instrument = $Instrument
            granularity = $Granularity
            lookback_days = $LookbackDays
            session_bucket = $SessionBucket
            session_window_utc = $SessionWindowUtc
        }
        result = @{
            job_id = $jobId
            job_status = $jobStatus
            alpha_latest_pointer_remote = "$AlphaRemoteRepo/ARTIFACTS/performance/latest_research_job_result.json"
            alpha_latest_pointer_local = $localLatestJson
            metrics = $latestMetrics
        }
        macbook_pull_commands = @(
            "mkdir -p ~/fxg-phase8-results",
            "gcloud compute scp --zone ""us-central1-a"" --project ""fxg-ai-trading"" ""fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_research_job_result.json"" ~/fxg-phase8-results/",
            "python3 -m json.tool ~/fxg-phase8-results/latest_research_job_result.json"
        )
    }
    ($report | ConvertTo-Json -Depth 12) | Out-File -FilePath $localFinalReport -Encoding utf8

    Write-Host "PHASE8N_ONE_CLICK_COMPLETE"
    Write-Host "job_id=$jobId"
    Write-Host "job_status=$jobStatus"
    Write-Host "alpha_result_pointer=$AlphaRemoteRepo/ARTIFACTS/performance/latest_research_job_result.json"
    Write-Host "instrument=$Instrument"
    Write-Host "granularity=$Granularity"
    Write-Host "lookback_days=$LookbackDays"
    Write-Host "session_bucket=$SessionBucket"
    Write-Host "replay_mode=$($latestMetrics.replay_mode)"
    Write-Host "candidate_count=$($latestMetrics.candidate_count)"
    Write-Host "expectancy_r=$($latestMetrics.expectancy_r)"
    Write-Host "profit_factor_r=$($latestMetrics.profit_factor_r)"
    Write-Host "max_loss_streak=$($latestMetrics.max_loss_streak)"
    Write-Host "drawdown_proxy_r=$($latestMetrics.drawdown_proxy_r)"
    Write-Host "recommendation_label=$($latestMetrics.recommendation_label)"
    Write-Host "news_reconstruction_available=$($latestMetrics.news_reconstruction_available)"
    Write-Host "calendar_reconstruction_available=$($latestMetrics.calendar_reconstruction_available)"
    Write-Host "ny_live_enabled=$($latestMetrics.ny_live_enabled)"
    Write-Host "send_trade_unlock_changed=$($latestMetrics.send_trade_unlock_changed)"
    Write-Host "execution_paths_changed=$($latestMetrics.execution_paths_changed)"
    Write-Host "local_final_report_json=$localFinalReport"
    Write-Host "MacBook pull commands:"
    Write-Host "  mkdir -p ~/fxg-phase8-results"
    Write-Host "  gcloud compute scp --zone ""us-central1-a"" --project ""fxg-ai-trading"" ""fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_research_job_result.json"" ~/fxg-phase8-results/"
    Write-Host "  python3 -m json.tool ~/fxg-phase8-results/latest_research_job_result.json"
    exit 0
} catch {
    try {
        $finishedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        $failReport = @{
            ok = $false
            phase = "Phase 8N"
            classification = "PHASE8N_ONE_CLICK_FINAL_REPORT"
            started_at_utc = $startedAtUtc
            finished_at_utc = $finishedAtUtc
            request = @{
                job_type = $JobType
                instrument = $Instrument
                granularity = $Granularity
                lookback_days = $LookbackDays
                session_bucket = $SessionBucket
                session_window_utc = $SessionWindowUtc
            }
            partial = @{
                job_id = $jobId
                job_status = $jobStatus
                alpha_latest_pointer_remote = "$AlphaRemoteRepo/ARTIFACTS/performance/latest_research_job_result.json"
                alpha_latest_pointer_local = $localLatestJson
            }
            error = "$($_.Exception.Message)"
        }
        ($failReport | ConvertTo-Json -Depth 10) | Out-File -FilePath $localFinalReport -Encoding utf8
    } catch { }
    Fail $_.Exception.Message
}


