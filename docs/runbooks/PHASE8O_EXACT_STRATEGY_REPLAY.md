# Phase 8O Exact Strategy Replay

Phase 8O is a research-only workflow for exact historical replay or explicit fail-closed proof. It must not place trades, call broker order APIs, use the MT5 bridge, edit runtime configuration, or change execution unlock policy.

## One-Click Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8o_one_click_exact_replay.ps1
```

Override example:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase8o_one_click_exact_replay.ps1 -Instrument EUR_USD -Granularity M15 -LookbackDays 90 -SessionBucket NY_OPEN_SECONDARY_PROPOSED
```

## What It Does

1. Runs local Phase 8 tests unless `-SkipTests` is passed.
2. Verifies ALPHA connectivity with `gcloud compute ssh`.
3. Deploys Phase 8O read-only scripts to ALPHA when missing.
4. Runs strategy discovery locally and on ALPHA.
5. Fails closed immediately if exact strategy, candidate, gate, indicator, or classification paths cannot be proven.
6. Exports OANDA historical candles plus news/calendar/context rows from ALPHA using read-only APIs.
7. Copies the compressed export to the 5950X.
8. Builds the local dataset with indicators, session labels, and UTC news/calendar embargo labels.
9. Runs archived-candidate exact replay only when required candidate fields are present.
10. Verifies the compact result pack is under 25 MB and has safe research flags.
11. Uploads and imports the compact pack to ALPHA.
12. Prints final metrics and MacBook pull commands.

## Classification

`PASS_EXACT_CANDIDATE_REPLAY_COMPLETE` means archived candidate rows had required live fields and were replayed against historical candles with same-bar SL-before-TP conservative resolution.

`FAIL_CLOSED_STRATEGY_LOGIC_NOT_FOUND` means exact strategy/candidate/gate fields could not be proven. No proxy replay is run.

`FAIL_CLOSED_NEWS_CALENDAR_UNRESOLVED` means required news/calendar reconstruction was unavailable or invalid. No clean exact replay is run.

## Safety Invariants

The result verifier rejects packs unless:

- `paper_review_only=true`
- `live_permission=false`
- `ny_live_enabled=false`
- `send_trade_unlock_changed=false`
- `execution_paths_changed=false`

The one-click script uses `gcloud compute ssh/scp` only. It does not restart services, edit `runtime/config.yaml`, or call execution bridges.

## Expected ALPHA Artifacts

- `ARTIFACTS/performance/latest_phase8o_strategy_discovery.json`
- `ARTIFACTS/performance/latest_phase8o_exact_replay_result.json`
- `ARTIFACTS/performance/latest_phase8o_backtest_summary.json`
- `ARTIFACTS/performance/latest_phase8o_recommendation.json`

## Local Artifacts

- `C:\Users\gavin\fxg-research\phase8o_exact_replay\data\phase8o_exact_replay_dataset.parquet`
- `C:\Users\gavin\fxg-research\phase8o_exact_replay\outputs\phase8o_result_pack.tar.gz`
- `C:\Users\gavin\fxg-research\phase8o_exact_replay\reports\phase8o_alpha_strategy_discovery.json`

If Parquet support is unavailable locally, the dataset builder writes a pickle fallback and records that in `phase8o_dataset_manifest.json`.

## Verification Commands

```powershell
python -m unittest discover -s tests -p "test_phase8*.py" -v
powershell -ExecutionPolicy Bypass -File scripts\phase8o_one_click_exact_replay.ps1
```

```bash
gcloud compute ssh --zone="us-central1-a" --project="fxg-ai-trading" "fxg-paper-e2-small-main-2026" --command="cd /opt/ai-quant && python3 -m json.tool ARTIFACTS/performance/latest_phase8o_strategy_discovery.json"
gcloud compute ssh --zone="us-central1-a" --project="fxg-ai-trading" "fxg-paper-e2-small-main-2026" --command="cd /opt/ai-quant && python3 -m json.tool ARTIFACTS/performance/latest_phase8o_backtest_summary.json"
gcloud compute ssh --zone="us-central1-a" --project="fxg-ai-trading" "fxg-paper-e2-small-main-2026" --command="cd /opt/ai-quant && python3 -m json.tool ARTIFACTS/performance/latest_phase8o_recommendation.json"
```

## MacBook Pull Commands

```bash
mkdir -p ~/fxg-phase8o-results
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_strategy_discovery.json" ~/fxg-phase8o-results/
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_backtest_summary.json" ~/fxg-phase8o-results/
gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_recommendation.json" ~/fxg-phase8o-results/
python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_strategy_discovery.json
python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_backtest_summary.json
python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_recommendation.json
```
