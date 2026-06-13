# Windows Sidecar Operator Quickstart

## What the Windows Sidecar Is

- **Read-only** HTTP API exposing MT5 account, positions, orders, symbols, and diagnostics.
- Bridge ID: `parallel_windows_sidecar_bridge_v1`
- Runs on Windows where MT5 is installed and logged in.
- Binds on port 8877 (localhost and/or LAN).

## What It Is Not

- **Not** the execution bridge. Execution stays on `canonical_mac_file_bridge_v1`.
- **Not** a trading endpoint. No send/close/preview routes.
- **Not** a replacement for the canonical bridge.

## How to Start

From repo root:

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_start_sidecar.ps1
```

Or MT5 + Sidecar together:

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_start_mt5_and_sidecar.ps1
```

## How to Stop

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_stop_sidecar.ps1
```

## How to Restart

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_restart_sidecar.ps1
```

## How to Check Status

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_status.ps1
```

Shows MT5 running, sidecar PID, bind URL, LAN URL, bridge ownership.

## How to Check Balance/Account

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_account_snapshot.ps1
```

Prints login, server, balance, equity, margin, profit.

## How to Verify Real Tick Data

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_healthcheck.ps1
```

Calls `/health`, `/diagnostics`, `/account`, `/symbols/EURUSD/tick`.

## How to Confirm Mac Dashboard Should Connect

1. Sidecar must bind on `0.0.0.0:8877` (set `BIND_HOST=0.0.0.0` in `.env`).
2. Windows firewall must allow TCP 8877 on Private profile.
3. Mac Control Plane must have `MT5_SIDECAR_BASE_URL=http://<Windows_LAN_IP>:8877` and matching `MT5_SIDECAR_API_KEY`.

## Shortcuts

Run once to create desktop shortcuts:

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_create_shortcuts.ps1
```

## Operator Warnings

### Do Not Rely on Sleeping PC for Market Execution

- **Do not** rely on a sleeping Windows PC for market-order execution.
- Wake-on-LAN generally requires a separate always-on device on the same network; Tailscale cannot directly wake a sleeping device without that helper.
- **Keep the trading PC awake during trading hours.**

### Test Trades Use Canonical Bridge

- Test trades must use `canonical_mac_file_bridge_v1`, not the sidecar.
- The sidecar is read-only and does not send orders.
