# Phase 8M: create a safe research job on ALPHA from this machine.
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [ValidateSet("phase8l_backtest", "phase8k_replay")]
    [string]$JobType = "phase8l_backtest",
    [string]$Instrument = "EUR_USD",
    [string]$Granularity = "M15",
    [int]$LookbackDays = 14
)

$ErrorActionPreference = "Stop"

$cmd = "cd $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8m_create_research_job.py --job-type $JobType --instrument $Instrument --granularity $Granularity --lookback-days $LookbackDays"
gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $cmd
if ($LASTEXITCODE -ne 0) { throw "PHASE8M_CREATE_JOB_FAILED" }

