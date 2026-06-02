#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== fxgdebugmt5 ==="
echo "Print mt5 preflight plus latest synced Windows telemetry summary."

python3 - <<'PY'
import json
import subprocess

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

rc, out, err = run(["python3", "-m", "src.operator_cli", "mt5_preflight"])
if rc != 0:
    print(json.dumps({"ok": False, "error": "mt5_preflight_failed", "stderr": err[:2000]}, indent=2))
    raise SystemExit(rc)

try:
    env = json.loads(out)
except Exception as exc:
    print(json.dumps({"ok": False, "error": f"mt5_preflight_json_parse_error:{exc}", "raw": out[:2000]}, indent=2))
    raise SystemExit(1)

payload = env.get("data") if isinstance(env, dict) and isinstance(env.get("data"), dict) else env
hb = (((payload.get("consumer_runtime_status") or {}).get("windows_consumer_heartbeat")) if isinstance(payload, dict) else None) or None
summary = {
    "preflight_status": payload.get("preflight_status") if isinstance(payload, dict) else None,
    "blocking_reason": payload.get("blocking_reason") if isinstance(payload, dict) else None,
    "exact_stop_point": payload.get("exact_stop_point") if isinstance(payload, dict) else None,
    "consumer_exclusive": payload.get("consumer_exclusive") if isinstance(payload, dict) else None,
    "windows_consumer_heartbeat": hb,
}
print(json.dumps(summary, indent=2, sort_keys=True))
PY

