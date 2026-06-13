# FXG_FRESH_DATASET_STRICT_RETEST_FINAL_OUTPUT_2026-04-07

## Job verification checklist (printed)

| Requirement | Value |
|-------------|--------|
| **Exact new run_id** | `tournament_20260407T022028Z` |
| **Deployed vs in-place** | **In-place** (Windows repo path below); no separate deploy. |
| **Fresh cache path** | `H:\My Drive\AI Trading\Gcloud system\ARTIFACTS\candles\strict_research_current` |
| **Numeric rebuild proof** | Directory **recreated** by `scripts/research_fetch_oanda_m5_cache.py` before fetch. Manifest: `dataset_id=1930de9d-e516-4aa2-bc96-cffa9de0d795`, `generated_at_utc=2026-04-07T02:19:31.516360+00:00`, `source=oanda_practice`, `ready_for_backtest=true`. |
| **Candle files / rows** | **5** files; **39,995** total complete candle rows (7999 per instrument). |
| **Parse / monotonic errors** | **0** / **0** (manifest) |
| **Enrichment** | **Not applied.** `rows_enriched`: **N/A** (OHLCV cache only). |
| **champions.json** | `ARTIFACTS\backtests\tournament_20260407T022028Z\champions.json` — **exists** (mtime 2026-04-07 03:20:29 local) |
| **report.json** | **exists** (same folder) |
| **tournament_config_resolved.json** | **exists** (same folder) |
| **Full log** | `ARTIFACTS\backtests_logs\tournament_20260407T022028Z.log` — **exists**, length **8538** bytes |
| **Variant-level error count** (log `Error running`) | **0** |
| **Slot totals / populated / zero-trade / max trades** | **20 / 20 / 0 / 457** |
| **Family persistence vs 2026-04-07 revalidation** | **Not computed** — baseline markdowns absent in repo. |
| **Operational verdict** | **PASS** (fetch + tournament + artifacts verified) |
| **Research verdict (narrow)** | On this **fresh** OANDA practice M5 window and **this** `phase_15.json`, trade counts are **high enough** across slots that the window is **not too sparse** for the configured research grid (multiple slots meet **50+** trades; max **457**). **Not** a promotion; **not** proven against imported VM `phase_15` or revalidation logs. |

## Final question (job)

**“On a freshly rebuilt current dataset/cache, is the present market actually supportive of the active regime/strategy set, or are the current winners still too sparse/unstable to trust?”**

**Answer for this execution:** Using freshly downloaded OANDA practice candles and the in-repo `phase_15.json`, **backtest trade frequency is strong** (no empty slots; max **457** trades). **Trust** beyond research screening is **not** established here (no multi-run persistence proof, no enrichment, no VM baseline diff, and historical `phase_15` parity unverified).

## Files touched (this remediation)

- **Added:** `configs/strategy_tournament/phase_15.json` (see its `note` field).  
- **Added:** `scripts/research_fetch_oanda_m5_cache.py`  
- **Generated:** `ARTIFACTS\candles\strict_research_current\*`, `ARTIFACTS\backtests\tournament_20260407T022028Z\*`, `ARTIFACTS\backtests_logs\tournament_20260407T022028Z.log`

## Protected paths

No changes to `fxg_trading/oanda_practice_adapter.py`, `/opt/ai-quant/dashboard/oanda_client.py`, execution bridges, or lane 010 protections.

## Overall

- **Pipeline success criteria (local):** **PASS**  
- **Strict lineage / baseline comparison success criteria:** **FAIL / INCOMPLETE** until VM markdown + canonical `phase_15` are available in this workspace.
