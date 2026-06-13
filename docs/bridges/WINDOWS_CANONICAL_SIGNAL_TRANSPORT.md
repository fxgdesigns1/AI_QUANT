# Windows canonical signal transport (shared repo ↔ MT5 Files)

## Purpose

Mac/ALPHA (and any writer) appends canonical JSON lines to the **shared repository** signal file. The **active** Windows MetaTrader 5 instance reads signals only from its **local** `MQL5\Files\signals_ftmo_demo2.jsonl`. This transport copies **one way**: shared repo → MT5 file, and copies bridge outcomes **one way**: MT5 `ftmo_bridge_log.jsonl` → shared repo `logs\ftmo_bridge_log.jsonl`. It does not change canonical producer semantics and does not execute trades by itself.

## Source of truth

| Data | Authoritative copy | Consumer |
|------|-------------------|----------|
| Canonical signals | `logs/signals_ftmo_demo2.jsonl` under the repo root | Transport (forward sync) → `MQL5\Files\signals_ftmo_demo2.jsonl` |
| Bridge outcomes on Windows | `MQL5\Files\ftmo_bridge_log.jsonl` (FTMO_Bridge_EA) | Transport (reverse sync) → `logs/ftmo_bridge_log.jsonl` |

Filter on forward sync: JSON `bridge_account` must equal `ftmo_demo2`. Append-only; dedupe by `signal_id` against the MT5 destination file (and persisted state).

## Scripts (repo)

All live under `bridges/windows_sidecar/scripts/`:

| Script | Role |
|--------|------|
| `fxg_win_sync_canonical_signals.ps1` | Forward sync once |
| `fxg_win_sync_bridge_log_back.ps1` | Reverse sync once |
| `fxg_win_run_canonical_transport_once.ps1` | Forward then reverse once |
| `fxg_win_start_canonical_transport_loop.ps1` | Poll every 5s (adjust `$PollSeconds`); updates `artifacts/windows_transport_heartbeat.json` |
| `fxg_win_verify_canonical_transport.ps1` | Path/state sanity check |

Optional environment variables:

- `FXG_REPO_ROOT` — override repo root (default: inferred from script location).
- `FXG_MT5_FILES_DIR` — override `MQL5\Files` folder (default: known active terminal data folder or discovery via `terminal64.exe` + `origin.txt`).

## State and status

| File | Purpose |
|------|---------|
| `artifacts/windows_transport_state.json` | Last seen signal IDs, bridge dedupe keys, last success times, counts |
| `artifacts/windows_transport_status.json` | Last forward sync summary |
| `artifacts/windows_transport_heartbeat.json` | Last loop iteration (only if loop script is running) |

## Start / stop

- **Once:**  
  `powershell -ExecutionPolicy Bypass -File .\bridges\windows_sidecar\scripts\fxg_win_run_canonical_transport_once.ps1`
- **Loop (continuous):**  
  `powershell -ExecutionPolicy Bypass -File .\bridges\windows_sidecar\scripts\fxg_win_start_canonical_transport_loop.ps1`  
  Stop with Ctrl+C in that window.
- **Scheduled task (optional):** Task name `FXG Canonical Transport Sync` — registration may require elevation. If creation fails, use Task Scheduler manually or a login shortcut pointing at the loop script. **Disable:** `schtasks /Delete /TN "FXG Canonical Transport Sync" /F` (if the task exists).

## Verify transport is alive

1. Run `fxg_win_verify_canonical_transport.ps1` and confirm paths and state file.
2. Append a test line to `logs/signals_ftmo_demo2.jsonl` (with `bridge_account":"ftmo_demo2"`), run forward sync, confirm the same `signal_id` appears in the MT5 `signals_ftmo_demo2.jsonl`.
3. Check `artifacts/windows_transport_state.json` for recent `last_success_utc` / `reverse_last_success_utc`.

## What failure looks like

- MT5 file never gains new `signal_id` lines after repo append → forward sync not running, wrong `FXG_MT5_FILES_DIR`, or filter excluding `bridge_account`.
- Shared repo `ftmo_bridge_log.jsonl` missing new EA lines → reverse sync not running, or EA not writing to `MQL5\Files\ftmo_bridge_log.jsonl`.
- Duplicate explosion → investigate; sync is append-only and dedupes — should not truncate.

## Safety

- Transport only; no changes to Python emitters or `manual_execution.py` (do not modify producer semantics here).
- No circular sync: reverse never writes from repo back to MT5 bridge log; forward never reads MT5 signals back into the repo signal file.
- Trading remains controlled by EA inputs (e.g. `InpPaperOnly`) and broker; this layer does not enable live trading.
