# Bridge Operator Runbook

## Canonical Bridge (canonical_mac_file_bridge_v1)
- **Do not** modify behavior, add duplicate writers, relabel, or write to canonical signal path.
- Check: ftmo_bridge_log.jsonl, systemd ai-quant-bridge.service

## Windows Sidecar (parallel_windows_sidecar_bridge_v1)
- Start: `bridges/windows_sidecar/scripts/start_windows_sidecar.ps1`
- Verify: `bridges/windows_sidecar/scripts/verify_windows_sidecar.ps1`
- Env: MT5_TERMINAL_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, SIDECAR_API_KEY

## Mock Sidecar (UI dev only)
- Port: 18877
- Env: MOCK_SIDECAR_PORT, SIDECAR_API_KEY, MOCK_SIDECAR_MODE
- **Not** real broker data.

## No Cross-Wire
- Sidecar never writes to canonical signal paths.
- Dashboard treats unreachable sidecar as `sidecar_unreachable`, not broker error.

## Operator Warnings

### Do Not Rely on Sleeping PC for Market Execution (CRITICAL)
- **Do not** rely on a sleeping Windows PC for market-order execution.
- Wake-on-LAN requires a separate always-on device on the same LAN; Tailscale cannot directly wake a sleeping device without that helper.
- **Keep the trading PC awake during trading hours.**
- Test trades must use `canonical_mac_file_bridge_v1`, not the sidecar.

### Test Trades Use Canonical Bridge
- Test trades must use `canonical_mac_file_bridge_v1`, not the sidecar.
