## Windows consumer telemetry lock-in (ALPHA)

### What this adds (telemetry-only)

- **EA heartbeat**: `ftmo_consumer_heartbeat.json` written by `FTMO_Bridge_EA.mq5` on init, every timer cycle, and deinit (overwrite mode, fail-open).
- **Synced artifact**: published to ALPHA as `/opt/ai-quant/ARTIFACTS/windows_consumer_heartbeat.json`.
- **Preflight**: `mt5_preflight` reads the synced heartbeat when present; if fresh+valid it becomes the **primary Windows consumer freshness evidence** (existing consumer-path checks remain as fallback evidence).

### Startup order (safe)

1. Start ALPHA services and dashboard (operator surface).
2. Open Windows MT5.
3. Attach `FTMO_Bridge_EA` to the intended chart.
4. Confirm the EA is writing `ftmo_consumer_heartbeat.json` to `MQL5/Files`.
5. Run Windows telemetry publish (sync).
6. Run `mt5_preflight` and confirm **fresh Windows consumer heartbeat** is present.
7. Only then: perform manual lane 010 emit using the existing canonical path.

### Shutdown order (safe)

1. Stop sending new manual trades.
2. Wait for a quiet state (no active order placement in flight).
3. Run one final telemetry publish (sync).
4. Close MT5 cleanly (EA deinit should write a final heartbeat).
5. Optionally stop operator-facing surfaces (dashboard) if desired.

### Debug shortcuts

- **Windows** (publish telemetry to ALPHA):

```powershell
PowerShell -ExecutionPolicy Bypass -File .\scripts\windows_sync_consumer_telemetry.ps1 -WhatIf
PowerShell -ExecutionPolicy Bypass -File .\scripts\windows_sync_consumer_telemetry.ps1
```

- **ALPHA / operator host** (read last synced heartbeat artifact):

```bash
bash scripts/fxgdebugconsumer.sh
```

- **ALPHA / operator host** (preflight + heartbeat in one view):

```bash
bash scripts/fxgdebugmt5.sh
```

