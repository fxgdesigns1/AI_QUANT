# Phase 8O: one-click exact replay or fail-closed result pack.
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [string]$AlphaExportRemoteDir = "/tmp/fxg_phase8o_exports",
    [string]$LocalRoot = "C:\Users\gavin\fxg-research\phase8o_exact_replay",
    [string]$Instrument = "EUR_USD",
    [string]$Granularity = "M15",
    [int]$LookbackDays = 90,
    [string]$SessionBucket = "NY_OPEN_SECONDARY_PROPOSED",
    [switch]$SkipTests,
    [switch]$SkipAlphaExport,
    [switch]$SkipCopyBackToAlpha,
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

function Test-AlphaFileExists([string]$RemotePath) {
    $probe = gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "test -f $RemotePath && echo __PHASE8O_FILE_OK__ || echo __PHASE8O_FILE_MISSING__"
    if ($LASTEXITCODE -ne 0) { return $false }
    return ($probe -match "__PHASE8O_FILE_OK__")
}

function Deploy-Phase8O {
    Write-Host "Deploying Phase 8O read-only script bundle to ALPHA..." -ForegroundColor DarkYellow
    $bundle = Join-Path $env:TEMP ("phase8o_remote_deploy_{0}.tgz" -f ([guid]::NewGuid().ToString("N")))
    try {
        Push-Location $RepoRoot
        tar czf $bundle `
            scripts/phase8o_find_exact_strategy_logic.py `
            scripts/phase8o_alpha_export_exact_replay_data.py `
            scripts/phase8o_verify_exact_replay_result.py `
            scripts/phase8s_calendar_budget_guard.py `
            scripts/local_research/oanda_mid_historical_fetch.py `
            scripts/local_research/phase8l_news_calendar_fetch.py `
            scripts/local_research/phase8l_dataset_builder.py `
            scripts/local_research/phase8k_replay_lib.py `
            scripts/local_research/phase8l_metrics.py `
            scripts/local_research/calendar_budgeted_client.py `
            scripts/local_research/rapidapi_economic_calendar_client.py `
            scripts/local_research/phase8p_replay_snapshot_schema.py
        if ($LASTEXITCODE -ne 0) { throw "LOCAL_TAR_DEPLOY_BUNDLE_FAILED" }
    } finally {
        Pop-Location
    }
    gcloud compute scp --zone $GcpZone --project $GcpProject $bundle "${AlphaVm}:/tmp/phase8o_remote_deploy.tgz"
    if ($LASTEXITCODE -ne 0) { throw "SCP_DEPLOY_BUNDLE_FAILED" }
    $ownedFiles = @(
        "$AlphaRemoteRepo/scripts/phase8o_find_exact_strategy_logic.py",
        "$AlphaRemoteRepo/scripts/phase8o_alpha_export_exact_replay_data.py",
        "$AlphaRemoteRepo/scripts/phase8o_verify_exact_replay_result.py",
        "$AlphaRemoteRepo/scripts/phase8s_calendar_budget_guard.py",
        "$AlphaRemoteRepo/scripts/local_research/oanda_mid_historical_fetch.py",
        "$AlphaRemoteRepo/scripts/local_research/phase8l_news_calendar_fetch.py",
        "$AlphaRemoteRepo/scripts/local_research/phase8l_dataset_builder.py",
        "$AlphaRemoteRepo/scripts/local_research/phase8k_replay_lib.py",
        "$AlphaRemoteRepo/scripts/local_research/phase8l_metrics.py",
        "$AlphaRemoteRepo/scripts/local_research/calendar_budgeted_client.py",
        "$AlphaRemoteRepo/scripts/local_research/rapidapi_economic_calendar_client.py",
        "$AlphaRemoteRepo/scripts/local_research/phase8p_replay_snapshot_schema.py"
    ) -join " "
    $untar = "sudo tar xzf /tmp/phase8o_remote_deploy.tgz -C $AlphaRemoteRepo && sudo chown aiquant:aiquant $ownedFiles && sudo chmod 644 $ownedFiles && sudo rm -f /tmp/phase8o_remote_deploy.tgz"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $untar
    if ($LASTEXITCODE -ne 0) { throw "REMOTE_UNTAR_FAILED" }
    Remove-Item -Force $bundle -ErrorAction SilentlyContinue
}

function Run-LocalFailClosedPack([string]$Reason) {
    Write-Step "Create local fail-closed result pack: $Reason"
    $argsReplay = @(
        (Join-Path $RepoRoot "scripts\phase8o_run_exact_strategy_replay.py"),
        "--strategy-discovery", $AlphaDiscoveryLocal,
        "--output-dir", $LocalOut,
        "--instrument", $Instrument,
        "--granularity", $Granularity,
        "--lookback-days", $LookbackDays,
        "--session-bucket", $SessionBucket,
        "--write-result-pack"
    )
    python @argsReplay
    if ($LASTEXITCODE -ne 0) { throw "LOCAL_FAIL_CLOSED_PACK_FAILED:$Reason" }
}

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$LocalData = Join-Path $LocalRoot "data"
$LocalOut = Join-Path $LocalRoot "outputs"
$LocalReports = Join-Path $LocalRoot "reports"
$LocalExportIncoming = Join-Path $LocalData "alpha_export_incoming"
New-Item -ItemType Directory -Force -Path $LocalData, $LocalOut, $LocalReports, $LocalExportIncoming | Out-Null

$LocalDiscovery = Join-Path $LocalReports "phase8o_local_strategy_discovery.json"
$AlphaDiscoveryLocal = Join-Path $LocalReports "phase8o_alpha_strategy_discovery.json"

if (-not $SkipTests) {
    Write-Step "1 Run local Phase 8 tests"
    Push-Location $RepoRoot
    try {
        python -m unittest discover -s tests -p "test_phase8*.py" -v
        if ($LASTEXITCODE -ne 0) { throw "LOCAL_TESTS_FAILED" }
    } finally {
        Pop-Location
    }
}

Write-Step "2 Verify ALPHA connectivity"
gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "echo CONNECT_OK && hostname && whoami"
if ($LASTEXITCODE -ne 0) { throw "ALPHA_CONNECTIVITY_FAILED" }

Write-Step "3 Deploy Phase 8O scripts to ALPHA"
Deploy-Phase8O

Write-Step "4 Run strategy discovery locally"
python (Join-Path $RepoRoot "scripts\phase8o_find_exact_strategy_logic.py") --repo-root $RepoRoot --output $LocalDiscovery
if ($LASTEXITCODE -ne 0) { throw "LOCAL_DISCOVERY_SCRIPT_FAILED" }

Write-Step "5 Run strategy discovery on ALPHA"
$remoteDiscoveryCmd = "cd $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8o_find_exact_strategy_logic.py --repo-root $AlphaRemoteRepo --output ARTIFACTS/performance/latest_phase8o_strategy_discovery.json"
gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $remoteDiscoveryCmd
if ($LASTEXITCODE -ne 0) { throw "ALPHA_DISCOVERY_SCRIPT_FAILED" }
gcloud compute scp --zone $GcpZone --project $GcpProject "${AlphaVm}:$AlphaRemoteRepo/ARTIFACTS/performance/latest_phase8o_strategy_discovery.json" $AlphaDiscoveryLocal
if ($LASTEXITCODE -ne 0) { throw "SCP_ALPHA_DISCOVERY_FAILED" }

$alphaDiscovery = Get-Content $AlphaDiscoveryLocal -Raw | ConvertFrom-Json
if ($alphaDiscovery.exact_replay_possible -ne $true) {
    Run-LocalFailClosedPack "strategy_discovery_failed"
} else {
    if (-not $SkipAlphaExport) {
        Write-Step "6 ALPHA dry-run exact replay export"
        $dryCmd = "cd $AlphaRemoteRepo && sudo -u aiquant bash -lc 'set -euo pipefail; set -a; source /etc/ai-quant/.env; set +a; $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8o_alpha_export_exact_replay_data.py --repo-root $AlphaRemoteRepo --days $LookbackDays --instruments $Instrument --granularities $Granularity,M5 --output-dir $AlphaExportRemoteDir --dry-run-plan'"
        gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $dryCmd
        if ($LASTEXITCODE -ne 0) { throw "ALPHA_EXPORT_DRY_RUN_FAILED" }

        Write-Step "7 ALPHA write exact replay export"
        $exportCmd = "cd $AlphaRemoteRepo && sudo -u aiquant bash -lc 'set -euo pipefail; set -a; source /etc/ai-quant/.env; set +a; $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8o_alpha_export_exact_replay_data.py --repo-root $AlphaRemoteRepo --days $LookbackDays --instruments $Instrument --granularities $Granularity,M5 --output-dir $AlphaExportRemoteDir --write-export'"
        gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $exportCmd
        if ($LASTEXITCODE -ne 0) { throw "ALPHA_EXPORT_FAILED" }

        Write-Step "8 Copy compressed export to 5950X"
        $bundleRemote = "/tmp/phase8o_export_bundle.tgz"
        $tarRemote = "sudo rm -f $bundleRemote && sudo tar czf $bundleRemote -C $AlphaExportRemoteDir ."
        gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $tarRemote
        if ($LASTEXITCODE -ne 0) { throw "ALPHA_EXPORT_TAR_FAILED" }
        $bundleLocal = Join-Path $LocalExportIncoming "phase8o_export_bundle.tgz"
        gcloud compute scp --zone $GcpZone --project $GcpProject "${AlphaVm}:$bundleRemote" $bundleLocal
        if ($LASTEXITCODE -ne 0) { throw "SCP_EXPORT_FROM_ALPHA_FAILED" }
        Get-ChildItem $LocalExportIncoming -File | Where-Object { $_.Name -ne "phase8o_export_bundle.tgz" } | Remove-Item -Force
        Get-ChildItem $LocalExportIncoming -Directory | Remove-Item -Recurse -Force
        tar -xzf $bundleLocal -C $LocalExportIncoming
        Remove-Item -Force $bundleLocal

        Write-Step "9 Clean ALPHA temp export files"
        gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "sudo rm -rf $AlphaExportRemoteDir $bundleRemote"
        if ($LASTEXITCODE -ne 0) { throw "ALPHA_EXPORT_CLEANUP_FAILED" }
    }

    Write-Step "10 Build local exact replay dataset"
    $buildArgs = @(
        (Join-Path $RepoRoot "scripts\phase8o_build_exact_replay_dataset.py"),
        "--alpha-export-dir", $LocalExportIncoming,
        "--local-root", $LocalRoot,
        "--primary-granularity", $Granularity
    )
    python @buildArgs
    if ($LASTEXITCODE -ne 0) {
        Run-LocalFailClosedPack "dataset_build_failed"
    } else {
        Write-Step "11 Run exact strategy replay locally"
        $datasetManifest = Join-Path $LocalData "phase8o_dataset_manifest.json"
        $datasetJson = Get-Content $datasetManifest -Raw | ConvertFrom-Json
        $datasetPath = $datasetJson.dataset_path
        $candidateArchive = Join-Path $LocalExportIncoming "candidate_context\latest_phase8h_archived_candidate_inventory.json"
        $replayArgs = @(
            (Join-Path $RepoRoot "scripts\phase8o_run_exact_strategy_replay.py"),
            "--dataset", $datasetPath,
            "--dataset-manifest", $datasetManifest,
            "--strategy-discovery", $AlphaDiscoveryLocal,
            "--candidate-archive", $candidateArchive,
            "--output-dir", $LocalOut,
            "--instrument", $Instrument,
            "--granularity", $Granularity,
            "--lookback-days", $LookbackDays,
            "--session-bucket", $SessionBucket,
            "--write-result-pack"
        )
        python @replayArgs
        if ($LASTEXITCODE -ne 0) { throw "LOCAL_EXACT_REPLAY_FAILED" }
    }
}

Write-Step "12 Verify local result pack"
$pack = Join-Path $LocalOut "phase8o_result_pack.tar.gz"
if (-not (Test-Path $pack)) { throw "PHASE8O_RESULT_PACK_MISSING" }
$packItem = Get-Item $pack
if ($packItem.Length -gt (25 * 1024 * 1024)) { throw "PHASE8O_RESULT_PACK_TOO_LARGE" }
python (Join-Path $RepoRoot "scripts\phase8o_verify_exact_replay_result.py") $pack
if ($LASTEXITCODE -ne 0) { throw "PHASE8O_RESULT_VERIFY_FAILED" }

if (-not $SkipCopyBackToAlpha) {
    Write-Step "13 Upload compact result pack to ALPHA"
    gcloud compute scp --zone $GcpZone --project $GcpProject $pack "${AlphaVm}:/tmp/phase8o_result_pack.tar.gz"
    if ($LASTEXITCODE -ne 0) { throw "SCP_RESULT_PACK_TO_ALPHA_FAILED" }

    Write-Step "14 Import result pack on ALPHA"
    $importCmd = "cd $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8o_verify_exact_replay_result.py /tmp/phase8o_result_pack.tar.gz --import-to-alpha --repo-root $AlphaRemoteRepo --strategy-discovery ARTIFACTS/performance/latest_phase8o_strategy_discovery.json"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $importCmd
    if ($LASTEXITCODE -ne 0) { throw "ALPHA_RESULT_IMPORT_FAILED" }
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "sudo rm -f /tmp/phase8o_result_pack.tar.gz"
}

Write-Step "15 Verify latest ALPHA pointers"
if (-not $SkipCopyBackToAlpha) {
    $pointerCmd = "cd $AlphaRemoteRepo && test -f ARTIFACTS/performance/latest_phase8o_strategy_discovery.json && test -f ARTIFACTS/performance/latest_phase8o_backtest_summary.json && test -f ARTIFACTS/performance/latest_phase8o_recommendation.json && echo PHASE8O_POINTERS_OK"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $pointerCmd
    if ($LASTEXITCODE -ne 0) { throw "ALPHA_POINTER_VERIFY_FAILED" }
}

$summaryPath = Join-Path $LocalOut "phase8o_backtest_summary.json"
$summary = Get-Content $summaryPath -Raw | ConvertFrom-Json
$status = if ($summary.classification -like "PASS_*") { "PHASE8O_EXACT_REPLAY_COMPLETE" } else { $summary.classification }

Write-Host ""
Write-Host "FINAL_SUMMARY" -ForegroundColor Green
Write-Host $status
Write-Host ("exact_strategy_replay=" + $summary.exact_strategy_replay)
Write-Host ("strategy_paths_found=" + (($summary.strategy_paths_found | ConvertTo-Json -Compress)))
Write-Host ("news_reconstruction_available=" + $summary.news_reconstruction_available)
Write-Host ("calendar_reconstruction_available=" + $summary.calendar_reconstruction_available)
Write-Host ("candidate_count=" + $summary.candidate_count)
Write-Host ("expectancy_r=" + $summary.expectancy_r)
Write-Host ("profit_factor_r=" + $summary.profit_factor_r)
Write-Host ("max_loss_streak=" + $summary.max_loss_streak)
Write-Host ("drawdown_proxy_r=" + $summary.drawdown_proxy_r)
Write-Host ("recommendation_label=" + $summary.recommendation_label)
Write-Host "ny_live_enabled=false"
Write-Host "send_trade_unlock_changed=false"
Write-Host "execution_paths_changed=false"
Write-Host ("result_pack_path=" + $pack)
Write-Host ""
Write-Host "MacBook pull commands:" -ForegroundColor Yellow
@(
    "mkdir -p ~/fxg-phase8o-results",
    'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_strategy_discovery.json" ~/fxg-phase8o-results/',
    'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_backtest_summary.json" ~/fxg-phase8o-results/',
    'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_recommendation.json" ~/fxg-phase8o-results/',
    "python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_strategy_discovery.json",
    "python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_backtest_summary.json",
    "python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_recommendation.json"
) | ForEach-Object { Write-Host $_ }
