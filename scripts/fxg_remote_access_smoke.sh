#!/bin/bash
# FXG Remote Access Smoke Test - quick overlay + sidecar check
REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
ARTIFACTS="$REPO_ROOT/artifacts"
CONFIG="$REPO_ROOT/src/control_plane/config/sidecar_target.json"
mkdir -p "$ARTIFACTS"

result='{"overlay_installed":false,"overlay_connected":false,"target_kind":"unset","sidecar_reachable":false,"mode":"remote_blocked"}'
command -v tailscale &>/dev/null && result=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); d['overlay_installed']=True; print(json.dumps(d))")
tailscale status &>/dev/null && result=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); d['overlay_connected']=True; print(json.dumps(d))")

BASE_URL=""
[ -f "$CONFIG" ] && BASE_URL=$(python3 -c "import json; d=json.load(open('$CONFIG')); print(d.get('base_url',''))" 2>/dev/null)
[ -z "$BASE_URL" ] && BASE_URL="$MT5_SIDECAR_BASE_URL"
[ -n "$BASE_URL" ] && result=$(echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
d['target_kind']='remote_overlay' if '100.' in '$BASE_URL' else 'home_lan'
print(json.dumps(d))
")

health=000
[ -n "$BASE_URL" ] && health=$(curl -s -o /dev/null -w "%{http_code}" -H "x-api-key: ${MT5_SIDECAR_API_KEY:-}" "$BASE_URL/health" 2>/dev/null || echo "000")
[ "$health" = "200" ] && result=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); d['sidecar_reachable']=True; d['mode']='remote_ready'; print(json.dumps(d))")

echo "$result" > "$ARTIFACTS/remote_access_smoke_latest.json"
cat "$ARTIFACTS/remote_access_smoke_latest.json"
