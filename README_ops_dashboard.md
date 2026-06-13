# FXG Dashboard Ops Guide

## Remote Access (Work / Non-Home Network)

Use Tailscale to reach the dashboard and Windows sidecar telemetry from anywhere:

1. **Windows**: `.\bridges\windows_sidecar\scripts\fxg_win_remote_overlay_setup.ps1`
2. **Mac**: `./scripts/fxg_switch_sidecar_target_remote_overlay.sh`
3. **Verify**: `./scripts/fxg_verify_remote_overlay_sidecar.sh`

See [docs/REMOTE_ACCESS_OPERATOR_GUIDE.md](docs/REMOTE_ACCESS_OPERATOR_GUIDE.md).

## Target Modes

- **home_lan**: Sidecar at 192.168.x.x (local only)
- **remote_overlay**: Sidecar via Tailscale (from work)

Dashboard shows `target_kind` in bridge panels. Switch via scripts; no manual file editing.

## Sidecar Role

Telemetry-only. Execution = canonical_mac_file_bridge_v1.
