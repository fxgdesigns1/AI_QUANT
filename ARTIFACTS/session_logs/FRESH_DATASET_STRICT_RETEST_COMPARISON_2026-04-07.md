# FRESH_DATASET_STRICT_RETEST_COMPARISON_2026-04-07

**Job:** FXG_FRESH_DATASET_STRICT_MARKET_REGIME_RETEST_V1  
**New run_id:** `tournament_20260407T022028Z`

## Comparison feasibility

| Baseline (job spec) | Present in this repo? |
|---------------------|------------------------|
| `ARTIFACTS/session_logs/REVALIDATION_PROGRESS_UPDATE_2026-04-07.md` | **No** |
| `ARTIFACTS/session_logs/STRICT_REVALIDATION_COMPARISON_2026-04-07.md` | **No** |
| `ARTIFACTS/session_logs/FXG_REVALIDATION_FINAL_OUTPUT_2026-04-07.md` | **No** |

Therefore **survived / stale / dropped / improved family classification vs the documented 2026-04-07 revalidation is not computed here** — importing those logs is required for an honest diff.

## New run — quantitative snapshot

**Data window (EUR_USD manifest sample):** ~`2026-02-26` → `2026-04-07` (7999 complete M5 bars). Other instruments similar (see `cache_manifest.json`).

**Tournament grid:** 4 variants × 5 instruments = **20** slots.

| Metric | Value |
|--------|--------|
| Populated slots | **20** |
| Zero-trade slots | **0** |
| Max trades (any slot) | **457** (`p15_sma_5_15` on `USD_JPY`) |
| Top trade counts (variant_id, instrument) | (457, USD_JPY), (440, EUR_USD), (440, AUD_USD), (438, GBP_USD), (434, XAU_USD) — all `p15_sma_5_15` |

**Champions file (score-ranked):** top entries include `p15_sma_5_20` and `p15_mom_5_20` on `GBP_USD` at **367** trades with identical metrics — expected because both strategies use the same crossover engine in `run_strategy_tournament.py` for these names.

## Current-market suitability (fresh rebuild, this config)

Under the job’s trade-count evidence bands, **this** freshly rebuilt OANDA practice M5 window shows **dense** activity: no zero-trade champions and multiple slots **≥ 50** trades (several **≥ 300**). That supports the narrow conclusion: **for this instrument set and SMA/momentum parameter grid, the recent window is not “too sparse to measure” in backtest.**

**Caveats:**

- **Not** a verdict on live edge, execution costs, or regime durability across independent runs (persistence rule in job).
- `phase_15.json` used here is **repo-authored** where VM copy was missing — comparison to a prior institutional `phase_15` is **unproven**.

## Required follow-up for strict lineage comparison

**YOU:** Supply the 2026-04-07 session markdown trio + canonical VM `phase_15.json` in this tree (or authorize CURSOR on that filesystem).
