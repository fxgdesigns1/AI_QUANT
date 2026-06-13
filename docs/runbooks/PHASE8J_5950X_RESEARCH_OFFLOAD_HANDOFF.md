## Phase 8J: 5950X Research-Offload Handoff (ALPHA Protected)

### Objective
Create a **repeatable, compact** handoff workflow that:
- **Exports only compact evidence inputs from ALPHA**
- Runs **heavy exact replay/backtesting only on the 5950X research estate**
- Imports back **only compact, verified result packs** into ALPHA artifacts

This workflow **does not** enable NY live, does not change execution logic, and must preserve:
- **lane 010**: manual_only protected
- **lane 011**: automated paper

### Non-negotiable safety rules
- **Do not place trades**
- **Do not call broker execution APIs for order placement**
- **Do not enable NY live execution**
- **Do not change Send Trade unlock logic**
- **Do not loosen fail-closed gates**
- **Do not edit `runtime/config.yaml`**
- **Do not run heavy replay / multi-month M5/M15 reconstruction on ALPHA**
- **Do not pull large OANDA historical datasets on ALPHA**
- **Do not copy candle caches back to ALPHA**
- **Do not copy the entire `ARTIFACTS/` tree**

### ALPHA-side: build a compact handoff pack (export)
Run on ALPHA repo (`/opt/ai-quant`):

```bash
cd /opt/ai-quant
python3 scripts/phase8j_build_5950x_handoff_pack.py
python3 -m json.tool ARTIFACTS/performance/latest_phase8j_5950x_handoff_manifest.json
ls -lh ARTIFACTS/performance/offloads/phase8j_5950x_handoff_pack_*.tar.gz | head
```

Outputs:
- `ARTIFACTS/performance/offloads/phase8j_5950x_handoff_pack_<UTC>.tar.gz`
- `ARTIFACTS/performance/offloads/phase8j_5950x_handoff_pack_<UTC>/manifest.json`
- `ARTIFACTS/performance/latest_phase8j_5950x_handoff_manifest.json`

The pack fails closed if required source artifacts are missing or the pack exceeds **25 MB**.

### Copy pack to 5950X research machine
On your laptop (or wherever you drive the copy):

```bash
mkdir -p ~/fxg-research/phase8j_replay && cd ~/fxg-research/phase8j_replay
gcloud compute scp --zone <ACTIVE_ALPHA_ZONE> --project fxg-ai-trading <ACTIVE_ALPHA_VM>:/opt/ai-quant/ARTIFACTS/performance/offloads/<PACK>.tar.gz ./
tar -xzf <PACK>.tar.gz
python3 -m json.tool <PACK_DIR>/manifest.json
```

### 5950X-side: run heavy replay locally only
This repo does **not** run heavy replay on ALPHA. The 5950X workflow is expected to:
- fetch/build datasets as needed (including OANDA history) on the research estate only
- run exact replay or best-available proxy replay
- emit a **compact result pack** meeting the Phase 8J contract

Result pack contract (max **25 MB**):
- `phase8j_replay_summary.json` (required)
- `phase8j_replay_samples_compact.jsonl` (optional but allowed)
- `phase8j_monthly_persistence.json` (required)
- `phase8j_recommendation.json` (required)
- `phase8j_run_manifest.json` (required)
- `checksums.sha256` (required)

Forbidden contents:
- `raw_candles/`, `candle_cache/`, `venv/`, `.git/`, `node_modules/`
- `.env`, secrets, large raw dumps

### Create the compact result pack (on 5950X)
Example:

```bash
tar -czf phase8j_5950x_result_pack.tar.gz \
  phase8j_replay_summary.json \
  phase8j_replay_samples_compact.jsonl \
  phase8j_monthly_persistence.json \
  phase8j_recommendation.json \
  phase8j_run_manifest.json \
  checksums.sha256
ls -lh phase8j_5950x_result_pack.tar.gz
```

### Copy result pack back to ALPHA (only if under cap)
```bash
gcloud compute scp --zone <ACTIVE_ALPHA_ZONE> --project fxg-ai-trading \
  phase8j_5950x_result_pack.tar.gz <ACTIVE_ALPHA_VM>:/tmp/
```

### ALPHA-side: verify then import (no execution changes)
Run on ALPHA repo (`/opt/ai-quant`), as the non-root runtime user if that’s the standard:

```bash
cd /opt/ai-quant
python3 scripts/phase8j_verify_5950x_result_pack.py /tmp/phase8j_5950x_result_pack.tar.gz
python3 scripts/phase8j_import_5950x_result_pack.py /tmp/phase8j_5950x_result_pack.tar.gz
```

Import destination:
- `ARTIFACTS/performance/imports/phase8j/<UTC>/`
- `ARTIFACTS/performance/latest_phase8j_5950x_import_manifest.json`

### Telegram reporting
This Phase 8J tooling does **not** automatically send Telegram messages.
If ALPHA already has a canonical Telegram sender, use it **manually** to send:
- the `latest_phase8j_5950x_handoff_manifest.json` after export
- the `latest_phase8j_5950x_import_manifest.json` after import

### What this workflow does NOT do
- It does **not** grant live permission
- It does **not** enable NY live
- It does **not** change lane policies
- It does **not** modify `runtime/config.yaml`
- It does **not** run heavy replay on ALPHA

