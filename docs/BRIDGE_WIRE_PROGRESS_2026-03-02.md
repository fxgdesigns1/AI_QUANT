# Multi-Terminal MT5 Bridge – Implementation Summary

**Date:** 2026-03-02  
**Status:** ✅ COMPLETE

---

## Goal

- Run 2 MT5 terminals (FTMO + CityTraders) and route signals to both
- One OANDA master account (010) generates signals
- Fanout: same approved signal copied to both prop accounts when enabled
- ONE TRADE PER SIGNAL: dedupe so EA cannot execute twice
- Execution OFF by default; explicit enable toggle per account

---

## Deliverables

### 1. Signal output files

| File | Purpose |
|------|---------|
| `logs/signals_prop_02.jsonl` | FTMO terminal |
| `logs/signals_citytraders.jsonl` | CityTraders terminal |
| `logs/signals.jsonl` | Backwards compatibility |

### 2. Config schema (`configs/bridge_accounts.json`)

- **Per account:** `id`, `enabled`, `mt5_signal_file`, `bridge_account_value`, `environment`, `magic_number`, `bridge_log_file`
- **routing_rules:** `fanout_enabled`, `fanout_targets`
- **master_feed:** `oanda_account_id` (default `"010"`), changeable via dashboard API

### 3. `scripts/generate_test_signal.py`

- `--fanout`: write to all enabled fanout targets
- `--signal-file`: override target file for testing

### 4. `scripts/bridge_wire_paths.py`

- Symlinks into both MT5 instances’ MQL5/Files:
  - `signals_prop_02.jsonl`, `signals_citytraders.jsonl`
- Collects `ftmo_bridge_log.jsonl`, `citytraders_bridge_log.jsonl` into `~/gcloud-system/logs/`
- Creates dedupe dirs and symlinks for EA

### 5. `scripts/verify_bridge_end_to_end.py`

- Verifies each target: emitted signal_id appears in correct bridge log
- `--fanout`: test fanout to all enabled targets
- Clear diagnostics if not found

### 6. Dashboard API

| Endpoint | Description |
|----------|-------------|
| `GET /api/bridge/state` | Accounts, last signals/log events per account, master_feed |
| `POST /api/accounts/enable` | `{id, enabled}` |
| `POST /api/master_feed` | `{oanda_account_id}` |

### 7. Dedupe

- `logs/dedupe/<account_id>/` per account
- Symlink `MQL5/Files/dedupe_<account_id>/` → `logs/dedupe/<account_id>/`
- EA can create `<signal_id>.done` when processed (persistent across restarts)

---

## Terminal commands

### Wiring

```bash
cd /path/to/Gcloud\ system
python3 scripts/bridge_wire_paths.py
```

### Start dashboard

```bash
./scripts/run_bridge_dashboard.sh
```

Or manually:

```bash
# Terminal 1: API
python3 -m uvicorn dashboard.bridge_api:app --host 127.0.0.1 --port 8788

# Terminal 2: Frontend
cd frontend/bridge-dashboard && npm run dev
```

Open http://127.0.0.1:5174

### Run full verification (fanout)

```bash
python3 scripts/verify_bridge_end_to_end.py --fanout --timeout 90
```

### Single-target verification

```bash
python3 scripts/verify_bridge_end_to_end.py --bridge-account prop_02 --timeout 90
```

### Generate test signal (fanout)

```bash
python3 scripts/generate_test_signal.py --fanout --machine
```

---

## Files changed/created

| File | Action |
|------|--------|
| `configs/bridge_accounts.json` | Updated schema v2 |
| `src/observability/bridge_signal_router.py` | New: fanout, multi-file emit |
| `src/observability/signal_exporter.py` | Delegates to bridge_router when fanout |
| `scripts/generate_test_signal.py` | `--fanout`, `--signal-file` |
| `scripts/bridge_wire_paths.py` | Multi-terminal wiring |
| `scripts/verify_bridge_end_to_end.py` | Per-target verification |
| `dashboard/bridge_api.py` | `POST /api/accounts/enable`, `POST /api/master_feed` |
| `dashboard/bridge_state_emitter.py` | Multi-account state |
| `frontend/bridge-dashboard/src/App.jsx` | Master feed, connected status, toggles |
| `docs/BRIDGE_WIRE_PROGRESS_2026-03-02.md` | This doc |
