#!/bin/bash
# FXG Remote Access - Human-readable status
REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
"$REPO_ROOT/scripts/fxg_remote_access_smoke.sh" "$REPO_ROOT" >/dev/null
ARTIFACTS="$REPO_ROOT/artifacts"
[ -f "$ARTIFACTS/remote_access_smoke_latest.json" ] || exit 1

python3 -c "
import json
d=json.load(open('$ARTIFACTS/remote_access_smoke_latest.json'))
print('=== Remote Access Status ===')
print('Overlay installed:', d.get('overlay_installed', False))
print('Overlay connected:', d.get('overlay_connected', False))
print('Target kind:', d.get('target_kind', 'unset'))
print('Sidecar reachable:', d.get('sidecar_reachable', False))
print('Mode:', d.get('mode', 'remote_blocked'))
"
