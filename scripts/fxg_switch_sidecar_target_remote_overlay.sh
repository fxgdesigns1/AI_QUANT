#!/bin/bash
# Switch dashboard sidecar target to remote_overlay (Tailscale)
set -e
REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
CONFIG_DIR="$REPO_ROOT/src/control_plane/config"
CONFIG_FILE="$CONFIG_DIR/sidecar_target.json"
ARTIFACTS="$REPO_ROOT/artifacts"
mkdir -p "$CONFIG_DIR" "$ARTIFACTS"

# Resolve Windows overlay address
BASE_URL=""
if [ -f "$ARTIFACTS/windows_remote_overlay_identity.json" ]; then
  BASE_URL=$(python3 -c "
import json,sys
d=json.load(open('$ARTIFACTS/windows_remote_overlay_identity.json'))
print(d.get('sidecar_base_url','') or '')
" 2>/dev/null || echo "")
fi
if [ -z "$BASE_URL" ] && [ -n "$2" ]; then
  BASE_URL="$2"
fi
if [ -z "$BASE_URL" ]; then
  echo "FAIL: No Windows overlay address. Run fxg_win_remote_overlay_setup.ps1 on Windows first, or pass URL: $0 <repo> http://100.x.x.x:8877"
  exit 1
fi

echo "{\"target_kind\":\"remote_overlay\",\"base_url\":\"$BASE_URL\",\"updated_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$CONFIG_FILE"
echo "Switched to remote_overlay: $BASE_URL"
echo '{"target_kind":"remote_overlay","base_url":"'"$BASE_URL"'","status":"ok"}' > "$ARTIFACTS/mac_remote_target_switch_result.json"
echo "PASS: Restart Control Plane if running to pick up change, or it will read on next request."
