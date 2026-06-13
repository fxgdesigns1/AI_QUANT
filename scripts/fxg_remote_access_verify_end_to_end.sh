#!/bin/bash
# FXG Remote Access - End-to-end verification (overlay path, NOT home LAN)
set -e
REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
ARTIFACTS="$REPO_ROOT/artifacts"
CONFIG="$REPO_ROOT/src/control_plane/config/sidecar_target.json"
mkdir -p "$ARTIFACTS"

BASE_URL=""
[ -f "$CONFIG" ] && BASE_URL=$(python3 -c "import json; d=json.load(open('$CONFIG')); print(d.get('base_url',''))" 2>/dev/null)
[ -z "$BASE_URL" ] && BASE_URL="$MT5_SIDECAR_BASE_URL"

# Reject home LAN as "remote" verification
if [[ "$BASE_URL" == *"192.168."* ]]; then
  echo "WARN: Target is home LAN. For remote verification, run fxg_switch_sidecar_target_remote_overlay.sh first."
fi

API_KEY="${MT5_SIDECAR_API_KEY:-}"
HEADERS=(); [ -n "$API_KEY" ] && HEADERS=(-H "x-api-key: $API_KEY")

health_ok=false; account_ok=false; tick_ok=false
[ -n "$BASE_URL" ] && {
  curl -sf "${HEADERS[@]}" "$BASE_URL/health" > /tmp/fxg_health.json 2>/dev/null && health_ok=true
  curl -sf "${HEADERS[@]}" "$BASE_URL/account" > /tmp/fxg_account.json 2>/dev/null && account_ok=true
  curl -sf "${HEADERS[@]}" "$BASE_URL/symbols/EURUSD/tick" > /tmp/fxg_tick.json 2>/dev/null && tick_ok=true
}

result=$(python3 -c "
import json
print(json.dumps({
  'health_ok': $health_ok,
  'account_ok': $account_ok,
  'tick_ok': $tick_ok,
  'base_url_set': bool('$BASE_URL'),
  'remote_verified': $health_ok and $account_ok
}))
")
echo "$result" > "$ARTIFACTS/remote_access_verify_latest.json"
echo "$result"
[ "$health_ok" = "true" ] && [ "$account_ok" = "true" ] && exit 0 || exit 1
