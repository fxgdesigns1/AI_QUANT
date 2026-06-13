#!/bin/bash
# FXG Remote Overlay Status
REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
CONFIG="$REPO_ROOT/src/control_plane/config/sidecar_target.json"
echo "=== Remote Overlay Status ==="
echo "tailscale: $(command -v tailscale 2>/dev/null || echo 'not installed')"
tailscale status 2>/dev/null || true
echo ""
if [ -f "$CONFIG" ]; then
  echo "sidecar_target.json:"
  cat "$CONFIG"
else
  echo "sidecar_target.json: not set (using MT5_SIDECAR_BASE_URL env)"
fi
