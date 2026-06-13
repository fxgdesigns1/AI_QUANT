# FRESH_DATASET_REBUILD_AND_RETEST_PROGRESS_UPDATE_2026-04-07

**Job:** FXG_FRESH_DATASET_STRICT_MARKET_REGIME_RETEST_V1  
**Execution:** In-place on Windows workspace `H:\My Drive\AI Trading\Gcloud system` (no separate VM deploy step).

## Verdict summary

| Stage | Status |
|-------|--------|
| Fresh OANDA M5 cache rebuild | **PASS** (numeric proof below) |
| Strict tournament (`phase_15.json`) | **PASS** |
| Required artifacts + full log | **PASS** |
| Comparison vs **imported** 2026-04-07 revalidation MDs | **INCOMPLETE** (those files were never present in this repo copy) |
| Strict lineage vs historical VM `phase_15` | **UNPROVEN** (`phase_15.json` was **created in-repo** 2026-04-07 — see below) |

## What was missing and how it was remediated

| Item | Status |
|------|--------|
| `configs/strategy_tournament/phase_15.json` | **Added** this session. The JSON includes a `note` field: canonical VM copy was absent; instruments were taken from `runtime/config.yaml` `default_instruments`; variants are only `sma_crossover_research` and `momentum_trading` (no new families). |
| `ARTIFACTS/session_logs/REVALIDATION_PROGRESS_UPDATE_2026-04-07.md` (etc.) | **Still missing** here — cannot restate prior 45/42/3/7-style stats from disk. |
| `docs/runbooks/STRICT_BACKTESTING_RULES.md` | **Still missing** in this workspace. |

## Fresh dataset / cache (rebuild proof)

**Fetcher:** `scripts/research_fetch_oanda_m5_cache.py` (clears output dir before write; loads `REPO_ROOT/.env` via `python-dotenv`).

**Cache directory (resolved):** `H:\My Drive\AI Trading\Gcloud system\ARTIFACTS\candles\strict_research_current`

**Manifest:** `ARTIFACTS\candles\strict_research_current\cache_manifest.json`

Verified fields from manifest (2026-04-07 run):

- `dataset_id`: `1930de9d-e516-4aa2-bc96-cffa9de0d795`
- `source`: `oanda_practice`
- `generated_at_utc`: `2026-04-07T02:19:31.516360+00:00`
- `candle_file_count`: **5**
- `total_candle_rows`: **39,995** (5 × 7,999 complete M5 rows)
- `parse_errors`: **0**
- `monotonic_errors_total`: **0**
- `ready_for_backtest`: **true**
- Per-instrument coverage (see manifest): e.g. EUR_USD `coverage_end` ≈ `2026-04-07T02:10:00.000000000Z` through ~late Feb–early Apr 2026 window (7999 bars each).

**Enrichment / news:** Not part of this candle-only path. **`rows_enriched` not applicable**; do not claim news enrichment.

## Tournament run

- **run_id:** `tournament_20260407T022028Z`
- **Config:** `configs\strategy_tournament\phase_15.json` (resolved cache path matches directory above).
- **Exit code:** 0
- **Log:** `ARTIFACTS\backtests_logs\tournament_20260407T022028Z.log`
- **Artifacts:** `ARTIFACTS\backtests\tournament_20260407T022028Z\` contains `champions.json`, `report.json`, `tournament_config_resolved.json`, `tournament_results.json`.
- **Variant-level errors** (log lines matching `Error running`): **0**

### Slot statistics (from `tournament_results.json`)

- **Slot total:** 20 (= 4 variants × 5 instruments)
- **Populated:** 20  
- **Zero-trade slots:** 0  
- **Max trades (any result row):** **457**

## Research interpretation (job bands)

- Several slots exceed **50** trades → **`paper_validation_candidate`** band per job rubric for those variants/pairs.
- **No promotion** to production/paper execution was performed or implied.

## Stop points / honesty

- This answers **fresh-data depth on the defined SMA/momentum grid**; it does **not** prove parity with a VM-only historical `phase_15` or with missing 2026-04-07 revalidation markdown baselines.

## Next action owner

**YOU:** Import the real VM `phase_15.json` and the three 2026-04-07 revalidation markdowns into this repo (or run diff there) if you need strict before/after family persistence.

**CURSOR:** Done for local fetch + tournament + logging to verified paths above.
