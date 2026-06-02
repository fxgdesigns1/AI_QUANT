#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== fxgstopsafe ==="
echo "Stops operator-facing dashboard (does not affect execution)."

bash "$ROOT/scripts/fxg_stop_dashboard.sh" || true

echo ""
echo "--- last known mt5 preflight (best-effort) ---"
python3 -m src.operator_cli mt5_preflight || true

