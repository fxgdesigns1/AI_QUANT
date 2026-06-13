# Windows Sidecar Maintenance and Debug

## Architecture and Ownership

| Role | Bridge ID | Location |
|------|-----------|----------|
| Execution | canonical_mac_file_bridge_v1 | Mac (file-based) |
| Data/Diagnostics | parallel_windows_sidecar_bridge_v1 | Windows sidecar |

The sidecar is **additive**. It does not replace the canonical bridge. Execution remains on the canonical bridge.

## Common Failure Modes

### 401 Unauthorized

- **Meaning:** API key mismatch or missing.
- **Fix:** Ensure `SIDECAR_API_KEY` in `bridges/windows_sidecar/.env` matches what the Mac dashboard (or client) sends in `x-api-key` header.

### Connection Refused

- **Meaning:** Sidecar is not running or not listening on the expected port.
- **Fix:** Run `fxg_win_start_sidecar.ps1`. Check with `fxg_win_status.ps1` and `netstat -ano | findstr :8877`.

### Localhost-Only Binding (Mac Can't Reach)

- **Meaning:** Sidecar listens on `127.0.0.1:8877` instead of `0.0.0.0:8877`.
- **Fix:** Set `BIND_HOST=0.0.0.0` in `bridges/windows_sidecar/.env`. Restart sidecar with `fxg_win_restart_sidecar.ps1`.

### Missing Market Watch Symbol (symbol_not_selected, symbol_not_found, symbol_name_mismatch, no_tick_data)

- **Meaning:** Symbol (e.g. EURUSD) not visible in MT5 Market Watch, or symbol does not exist, or broker uses a suffixed variant (e.g. EURUSDm), or tick data unavailable.
- **symbol_name_mismatch:** Broker uses a different symbol name (e.g. EURUSDm). The tick response includes `broker_symbol_actual`. Query `/symbols/{broker_symbol_actual}/tick` or add that symbol to Market Watch.
- **Fix:** The sidecar auto-selects the symbol in Market Watch (read-only safe) before failing. For symbol_name_mismatch, use the `broker_symbol_actual` from the response. Run `/symbols/probe/EURUSD` to discover broker variants.

### terminal_connected=false / account_connected=false

- **Meaning:** MT5 not running or not logged in.
- **Fix:** Start MT5, log in to the account, then restart sidecar.

## Inspect Autostart Task

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -match 'FXG|sidecar|8877' }
```

Task name: `FXG Windows Sidecar 8877` (if configured). State 3 = Disabled, 4 = Ready.

## Collect Support Bundle

```powershell
.\bridges\windows_sidecar\scripts\fxg_win_collect_support_bundle.ps1
```

Output: `artifacts/support_bundles/windows/fxg_sidecar_bundle_<timestamp>/`

Contains redacted env, netstat, health/diagnostics/account JSON, process info.

## Debug Scripts

- `fxg_win_debug_sidecar.ps1` – Process info, /health, /diagnostics, /account, /tick, failure bucket.
- `fxg_win_debug_bindings.ps1` – .env (redacted), netstat, firewall, LAN IP.

## Recover Without Touching Canonical Bridge

1. Stop sidecar: `fxg_win_stop_sidecar.ps1`
2. Fix .env (BIND_HOST, SIDECAR_API_KEY, MT5_TERMINAL_PATH).
3. Start MT5 and log in if needed.
4. Start sidecar: `fxg_win_start_sidecar.ps1`
5. Verify: `fxg_win_healthcheck.ps1`

No changes to `src/core/`, `configs/bridge_accounts.json`, or dashboard bridge routes are required.

## Operator Warnings

### Do Not Rely on Sleeping PC for Execution

- Do not rely on a sleeping Windows PC for market-order execution.
- Wake-on-LAN typically requires another always-on device on the same LAN; Tailscale cannot directly wake a sleeping device without that helper.
- Keep the trading PC awake during trading hours.

### Test Trades Use Canonical Bridge

- Test trades must go through `canonical_mac_file_bridge_v1`, not the sidecar.
- The sidecar is read-only and has no order send/close routes.
