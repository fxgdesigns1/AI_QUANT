#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== fxgdebugconsumer ==="
echo "Print latest synced Windows consumer heartbeat artifact (if present)."

python3 - <<'PY'
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = [
    root / "ARTIFACTS" / "windows_consumer_heartbeat.json",
    root / "artifacts" / "windows_consumer_heartbeat.json",
]
for p in paths:
    if p.is_file():
        try:
            doc = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            print(json.dumps({"ok": False, "path": str(p), "error": f"json_read_error:{exc}"}, indent=2))
            raise SystemExit(1)
        out = {
            "ok": True,
            "path": str(p),
            "ts_utc": doc.get("ts_utc"),
            "bridge_account": doc.get("bridge_account"),
            "ea_name": doc.get("ea_name"),
            "ea_version": doc.get("ea_version"),
            "chart_symbol": doc.get("chart_symbol"),
            "execution_enabled": doc.get("execution_enabled"),
            "kill_switch_enabled": doc.get("kill_switch_enabled"),
            "last_result_code": doc.get("last_result_code"),
            "latest_signal_id_seen": doc.get("latest_signal_id_seen"),
            "latest_signal_id_attempted": doc.get("latest_signal_id_attempted"),
            "latest_signal_id_executed_ok": doc.get("latest_signal_id_executed_ok"),
            "latest_signal_id_failed": doc.get("latest_signal_id_failed"),
            "validation_ok_count": doc.get("validation_ok_count"),
            "terminal_rejects_count": doc.get("terminal_rejects_count"),
            "lock_dedupe_hits_count": doc.get("lock_dedupe_hits_count"),
            "last_cycle_new_lines": doc.get("last_cycle_new_lines"),
        }
        print(json.dumps(out, indent=2))
        raise SystemExit(0)

print(json.dumps({"ok": False, "error": "windows_consumer_heartbeat_missing", "searched": [str(p) for p in paths]}, indent=2))
raise SystemExit(2)
PY

