# Phase 8Y Data Coverage + API Cost Optimizer

## Goal

Provide a fail-closed preflight gate that answers:

- What data coverage exists (candles/news/calendar/macro)?
- What windows are missing?
- How many API calls are estimated for the next batch?
- Is the batch safe to run without violating API budget/safety rules?

Phase 8Y is preflight-only and does not place trades.

## Hard Safety Guarantees

- Trading remains disabled (`ny_live_enabled=false`).
- No broker order APIs are used.
- Dry-run mode spends zero paid API calls.
- News/calendar APIs are not called per backtest job.
- Cache-first policy is enforced.
- Batch creation fails closed unless Phase 8Y reports safe and context pack verification passes.

## Artifacts

- Coverage manifest: `ARTIFACTS/performance/latest_phase8y_data_coverage_manifest.json`
- API cost estimate: `ARTIFACTS/performance/latest_phase8y_api_cost_estimate.json`
- Context pack manifest: `ARTIFACTS/performance/latest_phase8y_shared_context_pack_manifest.json`
- Context pack verification: `ARTIFACTS/performance/latest_phase8y_context_pack_verification.json`

## One-Click Commands

Dry-run preflight (no paid calls):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8y_one_click_preflight.ps1 -Instrument EUR_USD -LookbackDays 90 -DryRun -RequireNews -RequireCalendar
```

Build + verify shared context pack (still preflight-only):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8y_one_click_preflight.ps1 -Instrument EUR_USD -LookbackDays 90 -BuildContextPack -RequireNews -RequireCalendar -MaxPaidCalendarCalls 1
```

Run batch only after preflight passes:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8x_one_click_batch_tournament.ps1 -CreateJobsOnAlpha -MaxJobs 50 -MaxHours 6 -CalendarApiMaxCalls 3
```

## Script Responsibilities

- `scripts/phase8y_inventory_data_coverage.py`
  - Builds required-window coverage inventory.
  - Emits missing windows explicitly.
  - Computes exact replay readiness and `safe_to_run_batch`.
- `scripts/phase8y_estimate_api_cost.py`
  - Converts manifest gaps into estimated call budget.
  - Applies provider batching rules (RapidAPI one call per preflight window, cache reuse).
- `scripts/phase8y_build_shared_context_pack.py`
  - Bundles cached/preflight artifacts into a reusable shared pack.
  - Refuses to build if preflight is unsafe.
- `scripts/phase8y_verify_context_pack.py`
  - Verifies SHA-256 for all packed files.
  - Fails closed on missing/corrupt files.
- `scripts/phase8y_one_click_preflight.ps1`
  - Orchestrates inventory + cost + optional pack build/verify.
  - Returns pass/fail classification and gate state.

## Batch Gate

`scripts/phase8x_create_batch_jobs.py` now enforces Phase 8Y preflight by default:

- Requires `latest_phase8y_data_coverage_manifest.json` with `safe_to_run_batch=true`.
- Requires `latest_phase8y_context_pack_verification.json` with `all_files_verified=true`.
- Blocks if estimated paid calendar calls exceed requested cap.

Override exists for tests only:

- `--skip-phase8y-preflight`

## Dashboard Updates

Phase 8Y indicators are merged into dashboard outputs:

- Estimated calls needed next batch
- Estimated paid calendar calls
- Cache hit rate
- Exact replay readiness
- Missing windows count
- `safe_to_run_batch`

These flow from:

- `scripts/phase8p_build_research_dashboard.py`
- `scripts/phase8u_build_stitch_dashboard_payload.py`
- `scripts/phase8u_open_stitch_dashboard_preview.py`

## Verification Checklist

1. Run Phase 8Y dry-run preflight.
2. Confirm coverage + cost artifacts are written.
3. If using `-BuildContextPack`, confirm verification artifact is `all_files_verified=true`.
4. Confirm dashboard payload includes Phase 8Y fields.
5. Confirm batch job creation fails closed when preflight is unsafe.
