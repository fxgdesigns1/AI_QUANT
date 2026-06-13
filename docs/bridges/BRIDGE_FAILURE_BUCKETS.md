# Bridge Failure Buckets

## Canonical Mac File Bridge (canonical_mac_file_bridge_v1)
- `producer_fail`
- `transport_fail`
- `consumer_path_fail`
- `ea_parse_fail`
- `broker_reject_fail`
- `unknown_fail`

## Parallel Windows Sidecar (parallel_windows_sidecar_bridge_v1)
- `sidecar_unreachable`
- `terminal_not_running`
- `mt5_initialize_failed`
- `account_not_logged_in`
- `account_info_unavailable`
- `symbol_not_selected`
- `symbol_not_found`
- `symbol_name_mismatch` – Broker uses suffixed symbol (e.g. EURUSDm). Use `broker_symbol_actual` from response.
- `no_tick_data`
- `tick_stale`
- `history_unavailable`
- `write_guard_blocked`
- `broker_reject`
- `unknown_fail`

## Dashboard Rule
Bridge family must always be visible next to failure bucket.
