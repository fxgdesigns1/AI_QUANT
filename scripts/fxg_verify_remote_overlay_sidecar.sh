#!/bin/bash
# Verify sidecar reachability over remote overlay
set -e
REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
ARTIFACTS="$REPO_ROOT/artifacts"
CONFIG="$REPO_ROOT/src/control_plane/config/sidecar_target.json"
mkdir -p "$ARTIFACTS"

BASE_URL=""
if [ -f "$CONFIG" ]; then
  BASE_URL=$(python3 -c "import json; d=json.load(open('$CONFIG')); print(d.get('base_url',''))" 2>/dev/null)
fi
if [ -z "$BASE_URL" ]; then
  BASE_URL="$MT5_SIDECAR_BASE_URL"
fi
if [ -z "$BASE_URL" ]; then
  echo "FAIL: No sidecar target. Run fxg_switch_sidecar_target_remote_overlay.sh"
  exit 1
fi

API_KEY="${MT5_SIDECAR_API_KEY:-}"
HEADERS=()
[ -n "$API_KEY" ] && HEADERS=(-H "x-api-key: $API_KEY")

echo "Testing $BASE_URL..."
health=$(curl -s -o /dev/null -w "%{http_code}" "${HEADERS[@]}" "$BASE_URL/health" 2>/dev/null || echo "000")
account=$(curl -s -o /dev/null -w "%{http_code}" "${HEADERS[@]}" "$BASE_URL/account" 2>/dev/null || echo "000")
tick=$(curl -s -o /dev/null -w "%{http_code}" "${HEADERS[@]}" "$BASE_URL/symbols/EURUSD/tick" 2>/dev/null || echo "000")

echo "health=$health account=$account tick=$tick"
if [ "$health" = "200" ]; then
  echo "PASS: Sidecar reachable over overlay"
  echo "{\"health\":$health,\"account\":$account,\"tick\":$tick,\"reachable\":true}" > "$ARTIFACTS/mac_remote_overlay_status.json"
  exit 0
else
  echo "FAIL: Sidecar not reachable (health=$health)"
  echo "{\"health\":$health,\"account\":$account,\"tick\":$tick,\"reachable\":false}" > "$ARTIFACTS/mac_remote_overlay_status.json"
  exit 1
fi
