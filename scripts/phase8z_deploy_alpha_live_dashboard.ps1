# Phase 8Z: pack compact read-only dashboard + control-plane API patch, upload to ALPHA, extract, chown, restart control plane only.
# Does NOT restart ai-quant-runner. Does NOT copy .env or .secrets.
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRepo = "/opt/ai-quant",
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw "MISSING_PYTHON" }

$gc = $env:GCLOUD_PATH
if (-not $gc) { $gc = "gcloud" }

Write-Host "=== Phase 8Z local verification (unittest) ==="
Push-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot
$env:PYTHONIOENCODING = "utf-8"
& $py -m unittest discover -s tests -p "test_phase8*.py" -v
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "UNITTESTS_FAILED" }

Write-Host "=== Phase 8U payload refresh ==="
& $py scripts\phase8u_build_stitch_dashboard_payload.py --repo-root $RepoRoot --write
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "PHASE8U_PAYLOAD_FAILED" }

Write-Host "=== Mirror Stitch dashboard to ARTIFACTS (ALPHA serve path) ==="
$dashSrc = Join-Path $RepoRoot "dashboard\phase8_stitch_dashboard"
$dashDst = Join-Path $RepoRoot "ARTIFACTS\performance\phase8_stitch_dashboard"
New-Item -ItemType Directory -Force -Path $dashDst | Out-Null
Copy-Item -Force (Join-Path $dashSrc "index.html") $dashDst
Copy-Item -Force (Join-Path $dashSrc "app.js") $dashDst
Copy-Item -Force (Join-Path $dashSrc "styles.css") $dashDst

$artifactDir = Join-Path $RepoRoot "artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$tstamp = [DateTime]::UtcNow.ToString("yyyyMMdd'T'HHmmss'Z'")
$tarPath = Join-Path $artifactDir ("phase8z_alpha_live_dashboard_deploy_" + $tstamp + ".tar.gz")

Write-Host "=== Build tarball $tarPath ==="
tar -czf $tarPath `
    src/control_plane/api.py `
    dashboard/phase8_stitch_dashboard/index.html `
    dashboard/phase8_stitch_dashboard/app.js `
    dashboard/phase8_stitch_dashboard/styles.css `
    ARTIFACTS/performance/latest_stitch_dashboard_payload.json `
    ARTIFACTS/performance/latest_stitch_dashboard_contract.json `
    ARTIFACTS/performance/phase8_stitch_dashboard/index.html `
    ARTIFACTS/performance/phase8_stitch_dashboard/app.js `
    ARTIFACTS/performance/phase8_stitch_dashboard/styles.css `
    docs/runbooks/PHASE8Z_ALPHA_LIVE_DASHBOARD.md

if (-not (Test-Path $tarPath)) { Pop-Location; throw "TARBALL_MISSING" }

$remoteTar = "/tmp/phase8z_alpha_live_dashboard_deploy.tar.gz"
Write-Host "=== Upload to ALPHA ==="
& $gc compute scp $tarPath "${AlphaVm}:${remoteTar}" --zone $GcpZone --project $GcpProject
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "SCP_FAILED" }

$remoteCmd = @"
set -euo pipefail
sudo tar -xzf $remoteTar -C $AlphaRepo
sudo chown aiquant:aiquant `"$AlphaRepo/src/control_plane/api.py`"
sudo chown -R aiquant:aiquant `"$AlphaRepo/dashboard/phase8_stitch_dashboard`" `"$AlphaRepo/ARTIFACTS/performance/phase8_stitch_dashboard`"
sudo chown aiquant:aiquant `"$AlphaRepo/ARTIFACTS/performance/latest_stitch_dashboard_payload.json`" `"$AlphaRepo/ARTIFACTS/performance/latest_stitch_dashboard_contract.json`" 2>/dev/null || true
sudo chown aiquant:aiquant `"$AlphaRepo/docs/runbooks/PHASE8Z_ALPHA_LIVE_DASHBOARD.md`" 2>/dev/null || true
sudo find `"$AlphaRepo/dashboard/phase8_stitch_dashboard`" `"$AlphaRepo/ARTIFACTS/performance/phase8_stitch_dashboard`" -type f -exec chmod 0644 {} \; 2>/dev/null || true
sudo chmod 0644 `"$AlphaRepo/src/control_plane/api.py`" 2>/dev/null || true
sudo systemctl restart ai-quant-control-plane
rm -f $remoteTar
echo PHASE8Z_REMOTE_DEPLOY_DONE
"@

Write-Host "=== Extract on ALPHA + restart ai-quant-control-plane ==="
& $gc compute ssh --zone $GcpZone --project $GcpProject $AlphaVm --command $remoteCmd
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "REMOTE_DEPLOY_FAILED" }

Remove-Item -Force $tarPath -ErrorAction SilentlyContinue

Pop-Location

Write-Host ""
Write-Host "=== Desktop / MacBook (SSH tunnel - bind ONLY localhost) ==="
Write-Host "gcloud compute ssh --zone `"$GcpZone`" --project `"$GcpProject`" `"$AlphaVm`" -- -L 8787:127.0.0.1:8787"
Write-Host ""
Write-Host "Windows PowerShell then open browser:"
Write-Host 'Start-Process "http://127.0.0.1:8787/phase8/dashboard/"'
Write-Host ""
Write-Host "macOS:"
Write-Host 'open "http://127.0.0.1:8787/phase8/dashboard/"'
Write-Host ""
Write-Host "PASS Phase 8Z deploy script finished."
