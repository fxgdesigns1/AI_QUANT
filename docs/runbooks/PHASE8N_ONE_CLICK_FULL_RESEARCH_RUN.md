# Phase 8N — One-Click Full Research Run (PC/5950X)

## Goal

Run the full safe research cycle from the PC/5950X with **one command**:

- Create a research job on ALPHA (Phase 8M queue).
- Run the 5950X worker cycle(s) (heavy compute stays local).
- Verify ALPHA imported results and `latest_research_job_result.json`.
- Print final metrics and MacBook pull commands.
- Write a local final report JSON under `artifacts/`.

Non-goals:

- No trades.
- No broker order / execution APIs.
- No MT5 signal bridge.
- No ALPHA heavy compute.
- No `runtime/config.yaml` edits.
- No runner restart.

## One Command

Default run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8n_one_click_full_research_run.ps1
```

With overrides:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8n_one_click_full_research_run.ps1 -Instrument EUR_USD -Granularity M15 -LookbackDays 90 -SessionBucket NY_OPEN_SECONDARY_PROPOSED
```

## Parameters

- `-Instrument` (default `EUR_USD`)
- `-Granularity` (default `M15`)
- `-LookbackDays` (default `90`)
- `-SessionBucket` (default `NY_OPEN_SECONDARY_PROPOSED`)
- `-SessionWindowUtc` (default `13:30-16:00`)
- `-JobType` (default `phase8l_backtest`; allowed: `phase8l_backtest`, `phase8k_replay`)
- `-MaxWaitMinutes` (default `240`)
- `-PollSeconds` (default `20`)
- `-WorkerCyclesMax` (default `1`)
- `-SkipTests` (optional; skips `python -m unittest discover -s tests -p "test_phase8*.py" -v`)

## Outputs

- Local:
  - `artifacts/PHASE8N_latest_research_job_result_YYYYMMDDTHHMMSSZ.json` (downloaded from ALPHA)
  - `artifacts/PHASE8N_ONE_CLICK_FINAL_REPORT_YYYYMMDDTHHMMSSZ.json`
- ALPHA:
  - `/opt/ai-quant/ARTIFACTS/performance/latest_research_job_result.json` (updated by Phase 8M importer)

## Success Criteria (Console)

The script prints `PHASE8N_ONE_CLICK_COMPLETE` and includes:

- `job_id`, `job_status`, `alpha_result_pointer`
- `instrument`, `granularity`, `lookback_days`, `session_bucket`
- `replay_mode`, `candidate_count`, `expectancy_r`, `profit_factor_r`, `max_loss_streak`, `drawdown_proxy_r`, `recommendation_label`
- `news_reconstruction_available`, `calendar_reconstruction_available` (may print `True/False/` blank when unavailable)
- `ny_live_enabled`, `send_trade_unlock_changed`, `execution_paths_changed`
- MacBook pull commands

## Failure Modes (Fail Closed)

- ALPHA connectivity fails: script stops with the exact `gcloud` error.
- Phase 8M scripts missing on ALPHA: script stops (no ad-hoc deploy).
- Job creation fails: script stops and prints the create-job error output.
- Worker fails: script stops and reports `WORKER_ONCE_FAILED`.
- Latest pointer JSON missing/invalid: script stops and reports parser failure.
- Safety flags wrong anywhere: script stops (status parser fails closed).
- Result pack exceeds 25MB (from ALPHA import manifest): script stops.

## MacBook Pull Commands (printed by runner)

```bash
mkdir -p ~/fxg-phase8-results
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_research_job_result.json" ~/fxg-phase8-results/
python3 -m json.tool ~/fxg-phase8-results/latest_research_job_result.json
```

