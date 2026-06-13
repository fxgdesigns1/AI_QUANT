# Phase 8P: weekend-only weekly research cycle orchestrator for the 5950X.
# Heavy research stays local. ALPHA is used only for queueing, compact imports, and dashboard readback.

[CmdletBinding()]
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [int]$MaxWaitMinutes = 240,
    [switch]$DryRun,
    [switch]$SkipTests,
    [switch]$AllowWeekdayApiPull
)

$ErrorActionPreference = "Stop"

function Fail([string]$Msg) {
    Write-Host "PHASE8P_WEEKEND_RESEARCH_CYCLE_FAILED"
    Write-Host $Msg
    exit 1
}

function Require-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) { Fail "MISSING_REQUIRED_COMMAND:$Name" }
    return $cmd.Source
}

function Gcloud-Ssh([string]$RemoteCommand) {
    $cmd = @("compute", "ssh", "--quiet", "--zone", $GcpZone, "--project", $GcpProject, $AlphaVm, "--command", $RemoteCommand)
    $out = & gcloud @cmd 2>&1
    if ($LASTEXITCODE -ne 0) { throw "GCLOUD_SSH_FAILED:`n$out" }
    return ($out | Out-String)
}

function Gcloud-Scp([string]$Local, [string]$Remote) {
    $cmd = @("compute", "scp", "--quiet", "--zone", $GcpZone, "--project", $GcpProject, $Local, $Remote)
    $out = & gcloud @cmd 2>&1
    if ($LASTEXITCODE -ne 0) { throw "GCLOUD_SCP_FAILED:`n$out" }
    return ($out | Out-String)
}

function Deploy-Phase8PBundle {
    $bundle = Join-Path $env:TEMP ("phase8p_bundle_{0}.tgz" -f ([guid]::NewGuid().ToString("N")))
    Push-Location $RepoRoot
    try {
        tar czf $bundle `
            scripts/phase8p_index_research_results.py `
            scripts/phase8p_score_and_label_results.py `
            scripts/phase8p_build_research_dashboard.py `
            scripts/phase8p_retention_cleanup.py `
            docs/runbooks/PHASE8P_WEEKLY_RESEARCH_DASHBOARD.md
        if ($LASTEXITCODE -ne 0) { throw "PHASE8P_LOCAL_TAR_FAILED" }
    } finally {
        Pop-Location
    }
    Gcloud-Scp $bundle "${AlphaVm}:/tmp/phase8p_bundle.tgz" | Out-Null
    $remote = "sudo tar xzf /tmp/phase8p_bundle.tgz -C $AlphaRemoteRepo && sudo chown aiquant:aiquant $AlphaRemoteRepo/scripts/phase8p_*.py $AlphaRemoteRepo/docs/runbooks/PHASE8P_WEEKLY_RESEARCH_DASHBOARD.md && sudo rm -f /tmp/phase8p_bundle.tgz"
    Gcloud-Ssh $remote | Out-Null
    Remove-Item -Force $bundle -ErrorAction SilentlyContinue
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$StartedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$IsWeekend = @("Saturday", "Sunday") -contains (Get-Date).DayOfWeek.ToString()
$ArtifactsDir = Join-Path $RepoRoot "artifacts"
New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$FinalReport = Join-Path $ArtifactsDir "PHASE8P_WEEKEND_RESEARCH_CYCLE_$Stamp.json"

if ((-not $IsWeekend) -and (-not $AllowWeekdayApiPull)) {
    Fail "WEEKEND_ONLY_GUARD: run on Saturday/Sunday or pass -AllowWeekdayApiPull explicitly"
}

try {
    Require-Command "powershell" | Out-Null
    Require-Command "python" | Out-Null
    if (-not $DryRun) { Require-Command "gcloud" | Out-Null }

    if (-not $SkipTests) {
        Push-Location $RepoRoot
        try {
            python -m unittest discover -s tests -p "test_phase8*.py" -v
            if ($LASTEXITCODE -ne 0) { throw "LOCAL_TESTS_FAILED" }
        } finally {
            Pop-Location
        }
    }

    $jobs = @(
        @{
            job_type = "phase8o_exact_replay"
            instrument = "EUR_USD"
            granularity = "M15"
            lookback_days = 90
            session_bucket = "NY_OPEN_SECONDARY_PROPOSED"
            session_window_utc = "13:30-16:00"
        },
        @{
            job_type = "phase8l_backtest"
            instrument = "EUR_USD"
            granularity = "M15"
            lookback_days = 90
            session_bucket = "NY_OPEN_SECONDARY_PROPOSED"
            session_window_utc = "13:30-16:00"
        }
    )

    if ($DryRun) {
        $report = @{
            ok = $true
            phase = "Phase 8P"
            classification = "PHASE8P_DRY_RUN_PLAN"
            started_at_utc = $StartedAtUtc
            weekend_guard_passed = $true
            jobs_planned = $jobs
            dashboard_targets = @(
                "ARTIFACTS/performance/research_results_index.json",
                "ARTIFACTS/performance/latest_research_dashboard.json",
                "ARTIFACTS/performance/research_dashboard/index.html"
            )
            api_usage_weekend_only = $true
            paper_review_only = $true
            live_permission = $false
            ny_live_enabled = $false
            send_trade_unlock_changed = $false
            execution_paths_changed = $false
        }
        ($report | ConvertTo-Json -Depth 10) | Out-File -FilePath $FinalReport -Encoding utf8
        Write-Host "PHASE8P_DRY_RUN_OK"
        Write-Host "final_report=$FinalReport"
        exit 0
    }

    Gcloud-Ssh "echo PHASE8P_ALPHA_OK && test -d $AlphaRemoteRepo && echo PHASE8P_ALPHA_REPO_OK" | Out-Null

    $ran = @()
    Write-Host "PHASE8P_JOB_START phase8o_exact_replay"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "phase8o_one_click_exact_replay.ps1") `
        -GcpProject $GcpProject -GcpZone $GcpZone -AlphaVm $AlphaVm -AlphaRemoteRepo $AlphaRemoteRepo `
        -Instrument "EUR_USD" -Granularity "M15" -LookbackDays 90 -SessionBucket "NY_OPEN_SECONDARY_PROPOSED" -SkipTests
    if ($LASTEXITCODE -ne 0) { throw "PHASE8O_WEEKEND_JOB_FAILED" }
    $ran += "phase8o_exact_replay:EUR_USD:M15:90"

    Write-Host "PHASE8P_JOB_START phase8l_backtest"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "phase8n_one_click_full_research_run.ps1") `
        -GcpProject $GcpProject -GcpZone $GcpZone -AlphaVm $AlphaVm -AlphaRemoteRepo $AlphaRemoteRepo `
        -JobType "phase8l_backtest" -Instrument "EUR_USD" -Granularity "M15" -LookbackDays 90 `
        -SessionBucket "NY_OPEN_SECONDARY_PROPOSED" -SessionWindowUtc "13:30-16:00" -MaxWaitMinutes $MaxWaitMinutes -WorkerCyclesMax 1 -SkipTests
    if ($LASTEXITCODE -ne 0) { throw "PHASE8N_PHASE8L_WEEKEND_JOB_FAILED" }
    $ran += "phase8l_backtest:EUR_USD:M15:90"

    Deploy-Phase8PBundle

    $remoteBuild = "cd $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8p_index_research_results.py --repo-root $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8p_build_research_dashboard.py --repo-root $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8p_retention_cleanup.py --repo-root $AlphaRemoteRepo"
    $buildOut = Gcloud-Ssh $remoteBuild

    $verify = Gcloud-Ssh "cd $AlphaRemoteRepo && test -s ARTIFACTS/performance/latest_research_dashboard.json && test -s ARTIFACTS/performance/research_dashboard/index.html && echo PHASE8P_DASHBOARD_OK"
    if (-not $verify.Contains("PHASE8P_DASHBOARD_OK")) { throw "PHASE8P_ALPHA_DASHBOARD_VERIFY_FAILED" }

    $FinishedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $report = @{
        ok = $true
        phase = "Phase 8P"
        classification = "PASS_WEEKLY_RESEARCH_DASHBOARD_READY"
        started_at_utc = $StartedAtUtc
        finished_at_utc = $FinishedAtUtc
        jobs_ran = $ran
        alpha_dashboard_json = "$AlphaRemoteRepo/ARTIFACTS/performance/latest_research_dashboard.json"
        alpha_dashboard_html = "$AlphaRemoteRepo/ARTIFACTS/performance/research_dashboard/index.html"
        build_output = $buildOut
        weekly_cycle_ready = $true
        scheduler_installed = $false
        dashboard_built = $true
        dashboard_on_alpha = $true
        macbook_pull_commands = @(
            "mkdir -p ~/fxg-phase8p-dashboard",
            "gcloud compute scp --zone ""us-central1-a"" --project ""fxg-ai-trading"" --recurse ""fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/research_dashboard"" ~/fxg-phase8p-dashboard/",
            "open ~/fxg-phase8p-dashboard/research_dashboard/index.html"
        )
        paper_review_only = $true
        live_permission = $false
        ny_live_enabled = $false
        send_trade_unlock_changed = $false
        execution_paths_changed = $false
    }
    ($report | ConvertTo-Json -Depth 12) | Out-File -FilePath $FinalReport -Encoding utf8

    Write-Host "PHASE8P_WEEKEND_RESEARCH_CYCLE_COMPLETE"
    Write-Host "classification=PASS_WEEKLY_RESEARCH_DASHBOARD_READY"
    Write-Host "alpha_dashboard_json=$AlphaRemoteRepo/ARTIFACTS/performance/latest_research_dashboard.json"
    Write-Host "alpha_dashboard_html=$AlphaRemoteRepo/ARTIFACTS/performance/research_dashboard/index.html"
    Write-Host "local_final_report_json=$FinalReport"
    Write-Host "MacBook pull commands:"
    Write-Host "  mkdir -p ~/fxg-phase8p-dashboard"
    Write-Host "  gcloud compute scp --zone ""us-central1-a"" --project ""fxg-ai-trading"" --recurse ""fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/research_dashboard"" ~/fxg-phase8p-dashboard/"
    Write-Host "  open ~/fxg-phase8p-dashboard/research_dashboard/index.html"
    exit 0
} catch {
    $FinishedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $failReport = @{
        ok = $false
        phase = "Phase 8P"
        classification = "FAIL_CLOSED_WEEKLY_RESEARCH_DASHBOARD"
        started_at_utc = $StartedAtUtc
        finished_at_utc = $FinishedAtUtc
        error = "$($_.Exception.Message)"
        paper_review_only = $true
        live_permission = $false
        ny_live_enabled = $false
        send_trade_unlock_changed = $false
        execution_paths_changed = $false
    }
    ($failReport | ConvertTo-Json -Depth 10) | Out-File -FilePath $FinalReport -Encoding utf8
    Fail $_.Exception.Message
}
