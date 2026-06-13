#!/bin/bash
# Switch dashboard sidecar target to home_lan
set -e
REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
CONFIG_DIR="$REPO_ROOT/src/control_plane/config"
CONFIG_FILE="$CONFIG_DIR/sidecar_target.json"
ARTIFACTS="$REPO_ROOT/artifacts"
mkdir -p "$CONFIG_DIR" "$ARTIFACTS"

# Use env or arg for home LAN URL
BASE_URL="${2:-$MT5_SIDECAR_BASE_URL}"
if [ -z "$BASE_URL" ]; then
  BASE_URL="http://192.168.0.190:8877"
  echo "Using default home LAN: $BASE_URL (override with: $0 <repo> http://YOUR_LAN_IP:8877)"
fi

echo "{\"target_kind\":\"home_lan\",\"base_url\":\"$BASE_URL\",\"updated_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$CONFIG_FILE"
echo "Switched to home_lan: $BASE_URL"
echo '{"target_kind":"home_lan","base_url":"'"$BASE_URL"'","status":"ok"}' > "$ARTIFACTS/mac_remote_target_switch_result.json"
echo "PASS"
