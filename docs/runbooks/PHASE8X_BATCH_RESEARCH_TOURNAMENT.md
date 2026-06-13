# Phase 8X — Batch research tournament (5950X + ALPHA queue)

## Purpose

Queue many **research-only** Phase 8M jobs on ALPHA (`ARTIFACTS/research_jobs/queue/pending`), run heavy Phase 8L backtests on the **5950X** via the existing `phase8m_5950x_research_worker.py`, then refresh scoring, a tournament leaderboard JSON, and the Phase 8P / Stitch research dashboard.

No live trading, no broker order APIs, no `runtime/config.yaml` edits, no `ai-quant-runner` restarts.

## Matrix (default)

| Dimension | Values |
|-----------|--------|
| Instruments | EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CAD |
| Granularities | M5, M15, H1 |
| Lookbacks (days) | 90, 180, 365 |
| Sessions | LONDON_OPEN, NY_OPEN, NY_OPEN_SECONDARY_PROPOSED |
| Strategies | exact_current_alpha_strategy, session_breakout_with_news_embargo, trend_pullback_with_session_filter |

Default Cartesian size: **405** jobs.

Strategy keys are carried on the job as `strategy_name` / `research_strategy_key` and tune `rr_multiple` where the worker invokes Phase 8L. Session metrics on the 5950X use **NY** vs **LONDON** headline blocks based on `session_bucket` (see `phase8l_build_local_research_environment.py`).

## Commands

Dry-run (prints **exact** `exact_job_count` before creating jobs):

```text
powershell -ExecutionPolicy Bypass -File scripts\phase8x_one_click_batch_tournament.ps1 -DryRun
```

Overnight-style batch (cap worker cycles and wall time):

```text
powershell -ExecutionPolicy Bypass -File scripts\phase8x_one_click_batch_tournament.ps1 -MaxJobs 100 -MaxHours 10
```

Score-only (after results are imported into `ARTIFACTS/performance`):

```text
python scripts\phase8x_score_batch_results.py --repo-root .
```

Dashboard refresh (canonical):

```text
python scripts\phase8p_build_research_dashboard.py --repo-root .
```

## ALPHA queue placement

`scripts/phase8x_create_batch_jobs.py` writes pending job JSON files under:

`ARTIFACTS/research_jobs/queue/pending/`

When creating jobs from a Windows clone, **sync that `pending` tree to the ALPHA repo** (or run the create script on ALPHA) so the VM queue matches your intent. The 5950X worker then claims jobs through `gcloud compute ssh` as today.

## Calendar API budget

- Phase 8S monthly ledger still governs paid calendar HTTP on ALPHA.
- Job creation runs a **headroom** check: there must be room for `--calendar-api-max-calls` (default **3**) before the absolute monthly stop. Use `--skip-calendar-preflight` only in isolated test environments.
- Export path remains **cache-first** (`phase8l_alpha_export_research_data`); batch design assumes warmed calendar/news cache so jobs do not each force new paid calls.

## Promotion / proxy rules

- `scripts/phase8x_score_batch_results.py` applies stricter thresholds (minimum trades, PF, expectancy, drawdown, loss streak) and **demotes PROMOTE to CONTINUE** when `replay_mode` indicates proxy / best-available proxy reconstruction.
- **PROMOTE** still requires exact replay + news/calendar availability per Phase 8P scoring; tournament JSON lists `exact_replay_promotion_only` for audit.

## Artifacts

| Output | Path |
|--------|------|
| Tournament leaderboard | `ARTIFACTS/performance/phase8x_tournament_leaderboard.json` |
| Score batch report | `ARTIFACTS/performance/phase8x_score_batch_report.json` |
| Research dashboard JSON | `ARTIFACTS/performance/latest_research_dashboard.json` |
| Static HTML dashboard | `ARTIFACTS/performance/research_dashboard/index.html` |

## Verification checklist

1. `-DryRun` prints `exact_job_count` = **405** (or your capped `--max-jobs` value).
2. Pending JSON files validate via `scripts/phase8m_contract.py` / existing Phase 8M tests.
3. Worker completes at least one job without touching order execution modules.
4. `python scripts/phase8p_build_research_dashboard.py --repo-root .` exits 0 and updates dashboard JSON + HTML.

## Status

| Gate | Result |
|------|--------|
| PASS / FAIL / BLOCKED | Run pytest `tests/test_phase8x_batch_tournament.py` and a dry-run locally; record stdout as evidence. |
| Next owner | Operator runs queue sync + worker on 5950X; CURSOR maintains scripts. |
