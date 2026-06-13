# Phase 8L: One-click 5950X research environment + ALPHA export + optional result copy-back.
# Requires: gcloud CLI, Python 3, local repo checkout (defaults to parent of scripts/).
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [string]$AlphaExportRemoteDir = "/tmp/fxg_phase8l_exports",
    [string]$LocalRoot = "C:\Users\gavin\fxg-research\phase8l_environment",
    [string]$InputPackPath = "",
    [int]$Days = 14,
    [string]$Instruments = "EUR_USD",
    [string]$Granularities = "M15,M5",
    [switch]$SkipAlphaExport,
    [switch]$SkipCopyBackToAlpha,
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

function Test-AlphaFileExists([string]$RemotePath) {
    $probe = gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "test -f $RemotePath && echo __PHASE8L_FILE_OK__ || echo __PHASE8L_FILE_MISSING__"
    if ($LASTEXITCODE -ne 0) { return $false }
    return ($probe -match "__PHASE8L_FILE_OK__")
}

function Deploy-Phase8LRemoteScripts {
    Write-Host "Deploying Phase 8L script bundle to ALPHA (tar + scp + remote untar)..." -ForegroundColor DarkYellow
    $bundle = Join-Path $env:TEMP ("phase8l_remote_deploy_{0}.tgz" -f ([guid]::NewGuid().ToString("N")))
    try {
        Push-Location $RepoRoot
        tar czf $bundle `
            scripts/phase8l_alpha_export_research_data.py `
            scripts/phase8l_import_result_pack_to_alpha.py `
            scripts/phase8l_verify_result_pack.py `
            scripts/local_research/oanda_mid_historical_fetch.py
        if ($LASTEXITCODE -ne 0) { throw "LOCAL_TAR_DEPLOY_BUNDLE_FAILED" }
    } finally {
        Pop-Location
    }
    gcloud compute scp --zone $GcpZone --project $GcpProject $bundle "${AlphaVm}:/tmp/phase8l_remote_deploy.tgz"
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -Force $bundle -ErrorAction SilentlyContinue
        throw "SCP_DEPLOY_BUNDLE_FAILED"
    }
    $remoteTar = "/tmp/phase8l_remote_deploy.tgz"
    $untar = "sudo tar xzf $remoteTar -C $AlphaRemoteRepo && sudo mkdir -p $AlphaRemoteRepo/scripts/local_research && sudo chown aiquant:aiquant $AlphaRemoteRepo/scripts/phase8l_alpha_export_research_data.py $AlphaRemoteRepo/scripts/phase8l_import_result_pack_to_alpha.py $AlphaRemoteRepo/scripts/phase8l_verify_result_pack.py $AlphaRemoteRepo/scripts/local_research/oanda_mid_historical_fetch.py && sudo chmod 644 $AlphaRemoteRepo/scripts/phase8l_alpha_export_research_data.py $AlphaRemoteRepo/scripts/phase8l_import_result_pack_to_alpha.py $AlphaRemoteRepo/scripts/phase8l_verify_result_pack.py $AlphaRemoteRepo/scripts/local_research/oanda_mid_historical_fetch.py && sudo rm -f $remoteTar"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $untar
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -Force $bundle -ErrorAction SilentlyContinue
        throw "REMOTE_UNTAR_FAILED"
    }
    Remove-Item -Force $bundle -ErrorAction SilentlyContinue
}

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$LocalData = Join-Path $LocalRoot "data"
$LocalOut = Join-Path $LocalRoot "outputs"
$LocalExportIncoming = Join-Path $LocalData "alpha_export_incoming"
New-Item -ItemType Directory -Force -Path $LocalData, $LocalOut, $LocalExportIncoming | Out-Null

Write-Step "1 Verify ALPHA connectivity"
gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "echo CONNECT_OK && hostname && whoami"
if ($LASTEXITCODE -ne 0) { throw "ALPHA_SSH_FAILED" }

if (-not $SkipAlphaExport) {
    Write-Step "2 Deploy Phase 8L ALPHA scripts if missing"
    $remoteExporter = "$AlphaRemoteRepo/scripts/phase8l_alpha_export_research_data.py"
    $remoteOanda = "$AlphaRemoteRepo/scripts/local_research/oanda_mid_historical_fetch.py"
    if ((-not (Test-AlphaFileExists $remoteExporter)) -or (-not (Test-AlphaFileExists $remoteOanda))) {
        $localExporter = Join-Path $RepoRoot "scripts\phase8l_alpha_export_research_data.py"
        if (-not (Test-Path $localExporter)) { throw "MISSING_LOCAL_EXPORTER:$localExporter" }
        Deploy-Phase8LRemoteScripts
    }

    Write-Step "3 ALPHA dry-run export plan"
    $dryCmd = "cd $AlphaRemoteRepo && sudo -u aiquant bash -lc 'set -euo pipefail; set -a; source /etc/ai-quant/.env; set +a; $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8l_alpha_export_research_data.py --days $Days --instruments $Instruments --granularities $Granularities --output-dir $AlphaExportRemoteDir --dry-run-plan'"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $dryCmd
    if ($LASTEXITCODE -ne 0) { throw "ALPHA_DRY_RUN_FAILED" }

    Write-Step "4 ALPHA write export"
    $exportCmd = "cd $AlphaRemoteRepo && sudo -u aiquant bash -lc 'set -euo pipefail; set -a; source /etc/ai-quant/.env; set +a; $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8l_alpha_export_research_data.py --days $Days --instruments $Instruments --granularities $Granularities --output-dir $AlphaExportRemoteDir --write-export'"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $exportCmd
    if ($LASTEXITCODE -ne 0) { throw "ALPHA_EXPORT_FAILED" }

    Write-Step "5 Bundle and copy export from ALPHA to 5950X"
    $bundleRemote = "/tmp/phase8l_export_bundle.tgz"
    $tarRemote = "sudo rm -f $bundleRemote && sudo tar czf $bundleRemote -C $AlphaExportRemoteDir ."
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $tarRemote
    if ($LASTEXITCODE -ne 0) { throw "ALPHA_TAR_FAILED" }
    $bundleLocal = Join-Path $LocalExportIncoming "phase8l_export_bundle.tgz"
    gcloud compute scp --zone $GcpZone --project $GcpProject "${AlphaVm}:$bundleRemote" $bundleLocal
    if ($LASTEXITCODE -ne 0) { throw "SCP_FROM_ALPHA_FAILED" }
    Get-ChildItem $LocalExportIncoming -File | Where-Object { $_.Name -ne "phase8l_export_bundle.tgz" } | Remove-Item -Force
    tar -xzf $bundleLocal -C $LocalExportIncoming
    Remove-Item -Force $bundleLocal

    Write-Step "6 Clean ALPHA temp export"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "sudo rm -rf $AlphaExportRemoteDir $bundleRemote"
}

Write-Step "7 Build local research dataset + replay"
$manifestPath = Join-Path $LocalExportIncoming "phase8l_alpha_export_manifest.json"
if (-not (Test-Path $manifestPath)) {
    throw "MISSING_ALPHA_MANIFEST_UNDER:$LocalExportIncoming"
}

$buildArgs = @(
    (Join-Path $RepoRoot "scripts\phase8l_build_local_research_environment.py"),
    "--alpha-export-dir", $LocalExportIncoming,
    "--local-root", $LocalRoot,
    "--instrument", ($Instruments.Split(",")[0].Trim()),
    "--primary-granularity", "M15",
    "--write-result-pack"
)
if ($InputPackPath -and (Test-Path $InputPackPath)) {
    $buildArgs += @("--input-pack", $InputPackPath)
}
python @buildArgs
if ($LASTEXITCODE -ne 0) { throw "LOCAL_BUILD_FAILED" }

Write-Step "8 Verify local result pack"
$pack = Join-Path $LocalOut "phase8l_result_pack.tar.gz"
if (-not (Test-Path $pack)) { throw "RESULT_PACK_MISSING" }
$maxBytes = 25 * 1024 * 1024
$packItem = Get-Item $pack
if ($packItem.Length -gt $maxBytes) { throw "RESULT_PACK_TOO_LARGE" }
python (Join-Path $RepoRoot "scripts\phase8l_verify_result_pack.py") $pack
if ($LASTEXITCODE -ne 0) { throw "RESULT_PACK_VERIFY_FAILED" }

$summary = Get-Content (Join-Path $LocalOut "phase8l_backtest_summary.json") -Raw | ConvertFrom-Json
if ($summary.live_permission -eq $true -or $summary.ny_live_enabled -eq $true -or
    $summary.send_trade_unlock_changed -eq $true -or $summary.execution_paths_changed -eq $true) {
    throw "SAFETY_FLAGS_BLOCK_COPYBACK"
}

if (-not $SkipCopyBackToAlpha) {
    Write-Step "9 Copy result pack to ALPHA /tmp"
    gcloud compute scp --zone $GcpZone --project $GcpProject $pack "${AlphaVm}:/tmp/phase8l_result_pack.tar.gz"
    if ($LASTEXITCODE -ne 0) { throw "SCP_PACK_TO_ALPHA_FAILED" }

    Write-Step "9b Deploy importer/verifier on ALPHA if missing"
    $remoteImp = "$AlphaRemoteRepo/scripts/phase8l_import_result_pack_to_alpha.py"
    if (-not (Test-AlphaFileExists $remoteImp)) {
        Deploy-Phase8LRemoteScripts
    }

    Write-Step "9c Ensure ALPHA ARTIFACTS import tree exists (permissions only)"
    $artifactsPrep = "sudo mkdir -p $AlphaRemoteRepo/ARTIFACTS/performance/imports/phase8l && sudo chown -R aiquant:aiquant $AlphaRemoteRepo/ARTIFACTS/performance"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $artifactsPrep
    if ($LASTEXITCODE -ne 0) { throw "ALPHA_ARTIFACTS_PREP_FAILED" }

    Write-Step "10 Import on ALPHA"
    $impCmd = "cd $AlphaRemoteRepo && sudo -u aiquant $AlphaRemoteRepo/.venv/bin/python3 scripts/phase8l_import_result_pack_to_alpha.py /tmp/phase8l_result_pack.tar.gz"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $impCmd
    if ($LASTEXITCODE -ne 0) { throw "ALPHA_IMPORT_FAILED" }

    Write-Step "10b Remove ALPHA /tmp result pack after import"
    gcloud compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command "sudo rm -f /tmp/phase8l_result_pack.tar.gz"
}

Write-Host ""
Write-Host "FINAL_SUMMARY" -ForegroundColor Green
Write-Host ("environment_status=OK")
Write-Host ("dataset_start_utc=" + $summary.dataset_start_utc)
Write-Host ("dataset_end_utc=" + $summary.dataset_end_utc)
Write-Host ("granularities=" + ($summary.granularities -join ","))
Write-Host ("news_reconstruction_available=" + $summary.news_reconstruction_available)
Write-Host ("calendar_reconstruction_available=" + $summary.calendar_reconstruction_available)
Write-Host ("replay_mode=" + $summary.replay_mode)
Write-Host ("candidate_count=" + $summary.candidate_count)
Write-Host ("expectancy_r=" + $summary.expectancy_r)
Write-Host ("profit_factor_r=" + $summary.profit_factor_r)
Write-Host ("max_loss_streak=" + $summary.max_loss_streak)
Write-Host ("drawdown_proxy_r=" + $summary.drawdown_proxy_r)
Write-Host ("recommendation_label=" + $summary.recommendation_label)
Write-Host ("result_pack_path=" + $pack)
Write-Host ("alpha_cleaned=" + (-not $SkipAlphaExport))
Write-Host ("ny_live_enabled=" + $summary.ny_live_enabled)
Write-Host ("execution_paths_changed=" + $summary.execution_paths_changed)
Write-Host ""
Write-Host "MacBook pull commands:" -ForegroundColor Yellow
@(
    "mkdir -p ~/fxg-phase8l-results",
    'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_research_result_manifest.json" ~/fxg-phase8l-results/',
    'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_backtest_summary.json" ~/fxg-phase8l-results/',
    'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_recommendation.json" ~/fxg-phase8l-results/',
    "python3 -m json.tool ~/fxg-phase8l-results/latest_phase8l_backtest_summary.json",
    "python3 -m json.tool ~/fxg-phase8l-results/latest_phase8l_recommendation.json"
) | ForEach-Object { Write-Host $_ }
