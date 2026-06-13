# Phase 8L — One-Click Research Environment (ALPHA export → 5950X → optional ALPHA copy-back)

## Purpose

Build a **safe, read-only** research pipeline: ALPHA exports compressed candles and optional news/calendar context using existing environment credentials; the **5950X** performs dataset merge, indicators, session labels, gate-style embargo labels, replay/proxy backtest, metrics, and a **compact result pack** (≤25 MB). Optionally, the verified pack is copied back to ALPHA under `ARTIFACTS/performance/` for MacBook `gcloud scp` retrieval.

**This is not live permission.** `live_permission`, `ny_live_enabled`, and execution-path flags must remain false in all artifacts.

## Non-negotiables

- No trades, no broker order/execution APIs, no `runtime/config.yaml` edits, no `ai-quant-runner` restart.
- No secrets in manifests, packs, or logs; never print credentials.
- Do not copy raw candle caches or large datasets back to ALPHA—only the verified compact `phase8l_result_pack.tar.gz` and importer pointers.

## ALPHA — export only

Dry run (plan / size heuristic):

```bash
cd /opt/ai-quant && sudo -u aiquant bash -lc 'set -euo pipefail; set -a; source /etc/ai-quant/.env; set +a; /opt/ai-quant/.venv/bin/python3 scripts/phase8l_alpha_export_research_data.py --days 14 --instruments EUR_USD --granularities M15,M5 --output-dir /tmp/fxg_phase8l_exports --dry-run-plan'
```

Write export:

```bash
cd /opt/ai-quant && sudo -u aiquant bash -lc 'set -euo pipefail; set -a; source /etc/ai-quant/.env; set +a; /opt/ai-quant/.venv/bin/python3 scripts/phase8l_alpha_export_research_data.py --days 14 --instruments EUR_USD --granularities M15,M5 --output-dir /tmp/fxg_phase8l_exports --write-export'
```

Outputs include `phase8l_alpha_export_manifest.json`, `checksums.sha256`, gzip JSONL candles, and optional `phase8l_news_context_*` / `phase8l_calendar_context_*` files. If news/calendar keys are absent, manifests set `news_reconstruction_available` / `calendar_reconstruction_available` to false—**fail-closed** for news-clean claims downstream.

## 5950X — local build

Point `--alpha-export-dir` at the directory containing `phase8l_alpha_export_manifest.json` (after `scp` or the one-click bundle step). Optional `--input-pack` is a Phase 8J handoff pack directory for exact-replay inventory when fields exist.

```text
python scripts/phase8l_build_local_research_environment.py ^
  --alpha-export-dir "C:\Users\gavin\fxg-research\phase8l_environment\data\alpha_export_incoming" ^
  --local-root "C:\Users\gavin\fxg-research\phase8l_environment" ^
  --instrument EUR_USD ^
  --primary-granularity M15 ^
  --write-result-pack
```

Key outputs under `local_root`:

- `data/phase8l_research_dataset.parquet`, `data/phase8l_dataset_manifest.json`
- `outputs/phase8l_backtest_summary.json`, `outputs/phase8l_recommendation.json`, `outputs/phase8l_monthly_persistence.json`, `outputs/phase8l_daily_persistence.json`, `outputs/phase8l_run_manifest.json`, `outputs/phase8l_replay_samples_compact.jsonl`, `outputs/phase8l_result_pack.tar.gz`

## Verify result pack (before copy-back)

```text
python scripts/phase8l_verify_result_pack.py "C:\Users\gavin\fxg-research\phase8l_environment\outputs\phase8l_result_pack.tar.gz"
```

Rejects oversize packs, forbidden paths (`.env`, `raw_candles/`, `.git/`, etc.), bad checksums, missing summary fields, or unsafe flags.

## One-click PowerShell (5950X)

From repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8l_one_click_build_research_env.ps1
```

Flags:

- `-SkipAlphaExport` — use an export already placed under `%LocalRoot%\data\alpha_export_incoming\`
- `-SkipCopyBackToAlpha` — skip `scp` of the result pack and ALPHA import
- `-InputPackPath` — optional Phase 8J handoff pack directory on the PC

## ALPHA — import compact result pack

After `gcloud compute scp` of `phase8l_result_pack.tar.gz` to `/tmp/phase8l_result_pack.tar.gz`:

```bash
cd /opt/ai-quant && sudo -u aiquant /opt/ai-quant/.venv/bin/python3 scripts/phase8l_import_result_pack_to_alpha.py /tmp/phase8l_result_pack.tar.gz
```

Writes:

- `ARTIFACTS/performance/imports/phase8l/phase8l_import_<UTC>/…`
- `ARTIFACTS/performance/latest_phase8l_research_result_manifest.json`
- `ARTIFACTS/performance/latest_phase8l_backtest_summary.json`
- `ARTIFACTS/performance/latest_phase8l_recommendation.json`

## MacBook — pull latest summaries

The one-click script prints `gcloud compute scp` commands. Typical flow:

```bash
mkdir -p ~/fxg-phase8l-results
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" \
  "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_research_result_manifest.json" ~/fxg-phase8l-results/
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" \
  "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_backtest_summary.json" ~/fxg-phase8l-results/
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" \
  "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_recommendation.json" ~/fxg-phase8l-results/
python3 -m json.tool ~/fxg-phase8l-results/latest_phase8l_backtest_summary.json
```

## Tests

```bash
python -m unittest discover -s tests -p "test_phase8*.py" -v
```

## Verification status

| Milestone | Status | Evidence |
|-----------|--------|----------|
| Implementation | **PASS** / pending unittest | Repo paths under `scripts/`, `scripts/local_research/`, `tests/`, `docs/runbooks/` |

Run the unittest command locally and attach output for production sign-off.
