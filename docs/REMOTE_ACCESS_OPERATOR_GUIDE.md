# Remote Access Operator Guide

## Overview

Use the FXG dashboard and Windows sidecar telemetry from work or any non-home network via Tailscale (mesh VPN overlay). No home LAN IP dependency.

## Architecture

- **Sidecar**: Telemetry-only, read-only. No execution routes.
- **Execution owner**: canonical_mac_file_bridge_v1 (unchanged)
- **Target modes**: `home_lan` (local), `remote_overlay` (Tailscale)

## One-Click Setup

### Windows (Trading PC)

```powershell
Set-Location "H:\My Drive\AI Trading\Gcloud system"
.\bridges\windows_sidecar\scripts\fxg_win_remote_overlay_setup.ps1
```

If Tailscale prompts for sign-in, run `tailscale up` and complete auth. Re-run the setup to capture the overlay IP.

### Mac (Dashboard Host)

```bash
cd /path/to/Gcloud\ system
./scripts/fxg_remote_overlay_setup_mac.sh
./scripts/fxg_switch_sidecar_target_remote_overlay.sh
```

The switch script reads `artifacts/windows_remote_overlay_identity.json` (from Windows setup). Ensure that file is present (sync via Drive or run Windows setup first).

### Switch Targets

```bash
# Remote overlay (from work)
./scripts/fxg_switch_sidecar_target_remote_overlay.sh

# Home LAN (when at home)
./scripts/fxg_switch_sidecar_target_home_lan.sh
```

## Verify

```bash
./scripts/fxg_verify_remote_overlay_sidecar.sh
./scripts/fxg_remote_access_pretty.sh
```

## Dashboard

The dashboard shows `target_kind` (home_lan | remote_overlay | unset) in the bridge panels. No manual file editing needed—scripts update the config.

## Troubleshooting

- **Tailscale not connected**: Run `tailscale up` on both machines, sign in to same account.
- **Sidecar unreachable**: Ensure sidecar binds 0.0.0.0 (BIND_HOST in .env). Run `fxg_win_remote_overlay_setup.ps1` to add it.
- **Config not updating**: Control Plane reads `src/control_plane/config/sidecar_target.json` on each request. No restart needed.
