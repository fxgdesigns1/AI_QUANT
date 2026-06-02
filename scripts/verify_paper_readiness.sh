#!/usr/bin/env bash
# Verify paper execution readiness without placing orders
#
# Checks:
#   1) Control plane is running and healthy
#   2) mode == "paper"
#   3) execution_enabled == true
#   4) accounts_loaded > 0
#
# Never prints secrets; only prints boolean/integers and modes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

CP_BASE="${CP_BASE:-http://127.0.0.1:8787}"

echo "🔍 Verifying paper execution readiness..."
echo ""

# Check if control plane is running
if ! curl -sf "${CP_BASE}/health" >/dev/null 2>&1; then
    echo "❌ FAIL: Control plane not running or /health endpoint unavailable"
    echo "   Start with: bash scripts/start_control_plane_clean.sh"
    exit 1
fi

echo "✓ Control plane is running"

# Get status
STATUS_JSON=$(curl -sf "${CP_BASE}/api/status" 2>/dev/null || echo "")

if [[ -z "$STATUS_JSON" ]]; then
    echo "❌ FAIL: Could not fetch /api/status"
    exit 1
fi

# Parse JSON (using Python for portability, jq not guaranteed)
MODE=$(python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('mode', 'unknown'))" <<< "$STATUS_JSON")
EXEC_ENABLED=$(python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('execution_enabled', False))" <<< "$STATUS_JSON")
ACCOUNTS_LOADED=$(python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('accounts_loaded', 0))" <<< "$STATUS_JSON")
ACCOUNTS_EXEC_CAPABLE=$(python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('accounts_execution_capable', 0))" <<< "$STATUS_JSON")

echo "   Mode: $MODE"
echo "   Execution enabled: $EXEC_ENABLED"
echo "   Accounts loaded: $ACCOUNTS_LOADED"
echo "   Accounts execution capable: $ACCOUNTS_EXEC_CAPABLE"
echo ""

# Validate requirements
FAILED=0
FAIL_REASONS=()

if [[ "$MODE" != "paper" ]]; then
    FAILED=1
    FAIL_REASONS+=("mode is '$MODE' (expected 'paper')")
fi

if [[ "$EXEC_ENABLED" != "True" ]] && [[ "$EXEC_ENABLED" != "true" ]]; then
    FAILED=1
    FAIL_REASONS+=("execution_enabled is $EXEC_ENABLED (expected true)")
fi

if [[ "$ACCOUNTS_LOADED" -le 0 ]]; then
    FAILED=1
    FAIL_REASONS+=("accounts_loaded is $ACCOUNTS_LOADED (expected > 0)")
fi

if [[ $FAILED -eq 1 ]]; then
    echo "❌ FAIL: Paper execution not ready"
    echo ""
    echo "Missing requirements:"
    for reason in "${FAIL_REASONS[@]}"; do
        echo "   - $reason"
    done
    echo ""
    echo "To enable paper execution:"
    echo "   1) Set TRADING_MODE=paper (default)"
    echo "   2) Set PAPER_EXECUTION_ENABLED=true in .env"
    echo "   3) Ensure OANDA credentials are configured (OANDA_API_KEY, OANDA_ACCOUNT_ID)"
    echo "   4) Restart control plane and runner"
    exit 1
fi

echo "✅ PASS: Paper execution is ready"
echo ""
echo "System is configured for paper trading:"
echo "   - Mode: paper"
echo "   - Execution: enabled"
echo "   - Accounts: $ACCOUNTS_LOADED loaded, $ACCOUNTS_EXEC_CAPABLE execution-capable"
exit 0
