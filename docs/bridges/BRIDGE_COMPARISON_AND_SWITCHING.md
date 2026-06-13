# Bridge Comparison and Switching

## Three Separate Things

| Name | Bridge ID | Role |
|------|-----------|------|
| Canonical ALPHA MT5 Execution Bridge | canonical_mac_file_bridge_v1 | ONLY path for FTMO-facing trade signals from lane 010 |
| MT5 Sidecar Python FastAPI | parallel_windows_sidecar_bridge_v1 | Read-only account/price/diagnostics API |
| MT5 Sidecar Mock (UI validation only) | mock_sidecar_ui_validation_only | Synthetic HTTP server, same contract shape |
| Optional MT5 Export Bridge (MQL5 EA) | optional_mt5_file_export_bridge_v1 | Parallel read-only EA, alternative supplement |

## Switch State Model

| Function | Owner |
|----------|-------|
| Execution (lane 010) | canonical_mac_file_bridge_v1 |
| Account/positions/orders read | parallel_windows_sidecar_bridge_v1 (when running) |
| Diagnostics | Both (distinct failure buckets) |

## Future Cutover
- Explicit cutover plan only.
- No silent replacement.
- Dashboard shows both bridges distinctly; operator chooses.
