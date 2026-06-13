# Phase 8M — Remote Research Job Queue

## Goal

Use ALPHA as a safe research job queue and result store, while the 5950X pulls jobs and runs heavy research locally.

Flow:

1. Operator creates a research job on ALPHA.
2. 5950X worker polls ALPHA with `gcloud compute ssh/scp`.
3. Worker claims one pending job.
4. ALPHA prepares a compact read-only data input pack using existing credentials.
5. Worker downloads the input pack and runs Phase 8L or Phase 8K locally.
6. Worker verifies and uploads only a compact result pack.
7. ALPHA imports the result under `ARTIFACTS/performance/imports/research_jobs`.
8. Laptop/MacBook pulls `latest_research_job_result.json` later.

No inbound access to the 5950X is required.

## Safety Rules

- No trades.
- No broker order/execution APIs.
- No MT5 trade signal bridge.
- No runtime configuration edits.
- No runner restart.
- No heavy backtests on ALPHA.
- No secrets in jobs, packs, manifests, logs, or imports.
- Only compact verified results return to ALPHA.

## ALPHA Queue Paths

- Pending: `/opt/ai-quant/ARTIFACTS/research_jobs/queue/pending`
- Running: `/opt/ai-quant/ARTIFACTS/research_jobs/queue/running`
- Done: `/opt/ai-quant/ARTIFACTS/research_jobs/queue/done`
- Failed: `/opt/ai-quant/ARTIFACTS/research_jobs/queue/failed`
- Inputs: `/opt/ai-quant/ARTIFACTS/research_jobs/inputs`
- Result imports: `/opt/ai-quant/ARTIFACTS/performance/imports/research_jobs`
- Latest pointer: `/opt/ai-quant/ARTIFACTS/performance/latest_research_job_result.json`

## Create A Job

From any machine with ALPHA `gcloud` access:

```bash
gcloud compute ssh --zone="us-central1-a" --project="fxg-ai-trading" "fxg-paper-e2-small-main-2026" \
  --command="cd /opt/ai-quant && sudo -u aiquant /opt/ai-quant/.venv/bin/python3 scripts/phase8m_create_research_job.py --job-type phase8l_backtest --instrument EUR_USD --granularity M15 --lookback-days 14"
```

PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8m_submit_job_from_pc.ps1
```

Supported job types:

- `phase8l_backtest`: default 14-day EUR_USD M15 research environment.
- `phase8k_replay`: default 180-day EUR_USD M15 replay/proxy.

## List Jobs

```bash
gcloud compute ssh --zone="us-central1-a" --project="fxg-ai-trading" "fxg-paper-e2-small-main-2026" \
  --command="cd /opt/ai-quant && sudo -u aiquant /opt/ai-quant/.venv/bin/python3 scripts/phase8m_list_research_jobs.py"
```

## Run Worker Once On 5950X

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8m_worker_once.ps1
```

Dry run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8m_worker_once.ps1 -DryRun
```

## Run Worker Loop On 5950X

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8m_worker_loop.ps1 -SleepSeconds 60
```

## Pull Latest Result Later

```bash
mkdir -p ~/fxg-research-results
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" \
  "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_research_job_result.json" \
  ~/fxg-research-results/
python3 -m json.tool ~/fxg-research-results/latest_research_job_result.json
```

## Local Validation

```bash
python -m unittest discover -s tests -p "test_phase8*.py" -v
```

