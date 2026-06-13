# Phase 8P — Weekly Research Dashboard

## Goal

Phase 8P turns compact Phase 8M/8N/8O research imports into a readable weekly research dashboard and diary. It is research-only. Labels are review guidance and never enable live trading, NY live execution, Send Trade unlocks, or lane policy changes.

## Safety Rules

- Do not place trades.
- Do not call broker order or execution APIs.
- Do not edit `runtime/config.yaml`.
- Do not use the MT5 bridge for research jobs.
- Do not run heavy backtests on ALPHA.
- Do not copy raw candles, candle caches, `.env`, secrets, `.git`, `node_modules`, or `.venv` back to ALPHA.
- Store only compact verified summaries/results on ALPHA.

## Main Files

- `ARTIFACTS/performance/research_results_index.json`
- `ARTIFACTS/performance/research_results_index.jsonl`
- `ARTIFACTS/performance/latest_research_dashboard.json`
- `ARTIFACTS/performance/latest_weekend_research_diary.json`
- `ARTIFACTS/performance/research_dashboard/index.html`

## One-Click Weekend Run

From the 5950X Windows machine:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8p_weekend_research_cycle.ps1
```

Dry run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8p_weekend_research_cycle.ps1 -DryRun
```

The script is weekend-guarded by default. To run on a weekday, the operator must pass `-AllowWeekdayApiPull` explicitly.

## Install Saturday Scheduler

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8p_install_weekend_scheduler.ps1
```

Dry run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8p_install_weekend_scheduler.ps1 -DryRun
```

Default schedule is Saturday 08:00 local PC time. Do not install this task on ALPHA.

## Dashboard Labels

- `PROMOTE_REVIEW_CANDIDATE`: strong research evidence; prepare formal review pack only.
- `CONTINUE_FORWARD_PAPER_REVIEW`: promising but needs more evidence or exact/news/calendar confirmation.
- `WATCH_ONLY`: interesting but below review thresholds.
- `DEMOTE_RESEARCH_ONLY`: weak result; deprioritise.
- `BLOCK_OR_DOWNGRADE`: unacceptable loss streak, drawdown, or poor result.
- `FAIL_CLOSED_DATA_INCOMPLETE`: missing data, fail-closed replay, or invalid safety flags.

## Pull Dashboard From MacBook

```bash
mkdir -p ~/fxg-phase8p-dashboard
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" --recurse "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/research_dashboard" ~/fxg-phase8p-dashboard/
open ~/fxg-phase8p-dashboard/research_dashboard/index.html
```

## Local Verification

```powershell
python -m unittest discover -s tests -p "test_phase8*.py" -v
powershell -ExecutionPolicy Bypass -File scripts\phase8p_weekend_research_cycle.ps1 -DryRun
```

Milestone evidence must end with PASS / FAIL / BLOCKED, command evidence, and next action owner.
