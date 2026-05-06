#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== fxgstartsafe ==="
echo "Goal: bring operator-facing surfaces up, then print MT5 preflight + consumer heartbeat summary."

bash "$ROOT/scripts/fxg_start_real_mode.sh"

echo ""
echo "--- control-plane health ---"
python3 -m src.operator_cli health_check || true

echo ""
echo "--- mt5 preflight (authoritative) ---"
python3 -m src.operator_cli mt5_preflight || true

